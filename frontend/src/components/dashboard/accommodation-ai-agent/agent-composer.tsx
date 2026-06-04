"use client";

import React from "react";
import { Mic, MicOff, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  onboardingApi,
  type AccommodationAgentMessageResponse,
  type AccommodationChecklistItemState,
  type AccommodationPatch,
} from "@/lib/api";
import { HorizontalChipScroller } from "./horizontal-chip-scroller";

export type VoiceSessionContext = {
  accommodation_snapshot: Record<string, unknown>;
  checklist_state: AccommodationChecklistItemState[];
  focused_item_id: string | null;
  conversation_history: { role: "assistant" | "user" | "system"; content: string }[];
  pending_patch?: AccommodationPatch | null;
};

type AgentComposerProps = {
  disabled?: boolean;
  quickReplies: string[];
  voiceEnabled?: boolean;
  voiceContext?: VoiceSessionContext;
  placeholder?: string;
  onSend: (message: string) => void;
  onVoiceIngested?: (data: AccommodationAgentMessageResponse, transcript: string) => void;
};

const INGEST_DEBOUNCE_MS = 1100;
const MIN_PCM_BYTES = 6400;

type SpeechRecognitionCtor = new () => {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function buildVoiceIngestPayload(
  ctx: VoiceSessionContext,
  extras: { message?: string; audio_base64?: string; sample_rate?: number },
) {
  return {
    ...extras,
    focused_item_id: ctx.focused_item_id,
    checklist_state: ctx.checklist_state,
    accommodation_snapshot: {
      ...ctx.accommodation_snapshot,
      _agent_context: {
        pending_patch: ctx.pending_patch || {},
        active_item_id: ctx.focused_item_id,
        checklist_state: ctx.checklist_state,
        source: "voice",
      },
    },
    conversation_history: ctx.conversation_history.slice(-8),
  };
}

function confirmIngestion(reply: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(
    reply.length > 120 ? "Captured. Review the draft below." : reply,
  );
  utterance.rate = 1.05;
  window.speechSynthesis.speak(utterance);
}

export function AgentComposer({
  disabled,
  quickReplies,
  voiceEnabled = true,
  voiceContext,
  placeholder = "Type here...",
  onSend,
  onVoiceIngested,
}: AgentComposerProps) {
  const [text, setText] = React.useState("");
  const [voiceStatus, setVoiceStatus] = React.useState<string | null>(null);
  const [isRecording, setIsRecording] = React.useState(false);
  const voiceContextRef = React.useRef(voiceContext);
  voiceContextRef.current = voiceContext;
  const speechRef = React.useRef<InstanceType<SpeechRecognitionCtor> | null>(null);
  const ingestDebounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastIngestedRef = React.useRef("");
  const pendingTranscriptRef = React.useRef("");
  const pcmChunksRef = React.useRef<Int16Array[]>([]);
  const ingestInFlightRef = React.useRef(false);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const mediaStreamRef = React.useRef<MediaStream | null>(null);
  const workletNodeRef = React.useRef<AudioNode | null>(null);
  const silentGainRef = React.useRef<GainNode | null>(null);
  const useBrowserSttRef = React.useRef(false);
  const isRecordingRef = React.useRef(false);

  const submit = (value = text) => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const ingestTranscript = React.useCallback(
    async (transcript: string) => {
      const trimmed = transcript.trim();
      const ctx = voiceContextRef.current;
      if (!trimmed || !ctx || disabled || ingestInFlightRef.current) return;
      if (trimmed === lastIngestedRef.current) return;

      ingestInFlightRef.current = true;
      lastIngestedRef.current = trimmed;
      setVoiceStatus("Updating profile draft from your voice…");

      try {
        const response = await onboardingApi.ingestAccommodationVoice(
          buildVoiceIngestPayload(ctx, { message: trimmed }),
        );
        if (response.success && response.data) {
          const data = response.data;
          const patch = data.suggested_patch || {};
          const hasPatch = Object.entries(patch).some(([, v]) =>
            Array.isArray(v) ? v.length > 0 : v !== undefined && v !== null && v !== "",
          );
          onVoiceIngested?.(data, trimmed);
          setVoiceStatus(
            hasPatch
              ? "Draft ready — review and tap Apply."
              : data.reply || "Heard you. Add more detail or type the fact.",
          );
          confirmIngestion(hasPatch ? "Captured. Review the draft below." : data.reply);
        } else {
          setVoiceStatus(response.error || "Voice ingestion failed — try typing the fact.");
          lastIngestedRef.current = "";
        }
      } catch {
        setVoiceStatus("Voice ingestion failed — try typing the fact.");
        lastIngestedRef.current = "";
      } finally {
        ingestInFlightRef.current = false;
      }
    },
    [disabled, onVoiceIngested],
  );

  const scheduleIngest = React.useCallback(
    (transcript: string) => {
      pendingTranscriptRef.current = transcript;
      if (ingestDebounceRef.current) clearTimeout(ingestDebounceRef.current);
      ingestDebounceRef.current = setTimeout(() => {
        void ingestTranscript(transcript);
      }, INGEST_DEBOUNCE_MS);
    },
    [ingestTranscript],
  );

  const flushScheduledIngest = React.useCallback(() => {
    if (ingestDebounceRef.current) {
      clearTimeout(ingestDebounceRef.current);
      ingestDebounceRef.current = null;
    }
    const pending = pendingTranscriptRef.current.trim();
    if (pending) void ingestTranscript(pending);
  }, [ingestTranscript]);

  const ingestRecordedAudio = React.useCallback(async () => {
    const ctx = voiceContextRef.current;
    if (!ctx || disabled) return;
    const chunks = pcmChunksRef.current;
    pcmChunksRef.current = [];
    if (!chunks.length) return;

    let total = 0;
    for (const chunk of chunks) total += chunk.length;
    if (total * 2 < MIN_PCM_BYTES) {
      setVoiceStatus("Recording too short — speak a full fact, then tap Stop.");
      return;
    }

    const merged = new Int16Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    const bytes = new Uint8Array(merged.buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    const audioBase64 = btoa(binary);
    const sampleRate = audioContextRef.current?.sampleRate || 16000;

    ingestInFlightRef.current = true;
    setVoiceStatus("Transcribing and updating profile draft…");
    try {
      const response = await onboardingApi.ingestAccommodationVoice(
        buildVoiceIngestPayload(ctx, { audio_base64: audioBase64, sample_rate: sampleRate }),
      );
      const transcript = String(response.data?.metadata?.transcript || "").trim();
      if (response.success && response.data && transcript) {
        lastIngestedRef.current = transcript;
        if (onVoiceIngested) onVoiceIngested(response.data, transcript);
        setVoiceStatus("Draft ready — review and tap Apply.");
        confirmIngestion("Captured. Review the draft below.");
      } else {
        setVoiceStatus(response.error || "Could not transcribe — try again or type it.");
      }
    } catch {
      setVoiceStatus("Voice ingestion failed — try typing the fact.");
    } finally {
      ingestInFlightRef.current = false;
    }
  }, [disabled, onVoiceIngested]);

  const stopVoice = React.useCallback(
    async (options?: { clearStatus?: boolean }) => {
      if (ingestDebounceRef.current) {
        clearTimeout(ingestDebounceRef.current);
        ingestDebounceRef.current = null;
      }
      speechRef.current?.stop();
      speechRef.current = null;
      workletNodeRef.current?.disconnect();
      workletNodeRef.current = null;
      silentGainRef.current?.disconnect();
      silentGainRef.current = null;
      void audioContextRef.current?.close();
      audioContextRef.current = null;
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;

      if (useBrowserSttRef.current) {
        flushScheduledIngest();
      } else if (pcmChunksRef.current.length) {
        await ingestRecordedAudio();
      }

      pcmChunksRef.current = [];
      isRecordingRef.current = false;
      setIsRecording(false);
      if (options?.clearStatus !== false) setVoiceStatus(null);
    },
    [flushScheduledIngest, ingestRecordedAudio],
  );

  React.useEffect(() => () => void stopVoice(), [stopVoice]);

  const startSpeechRecognition = React.useCallback(() => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: SpeechRecognitionCtor }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionCtor }).webkitSpeechRecognition;
    if (!SpeechRecognition) return false;

    const langs = voiceContextRef.current?.accommodation_snapshot?.languages;
    const langList = Array.isArray(langs) ? langs.map(String) : [];
    const lang = langList.some((l) => l.toLowerCase().startsWith("hr")) ? "hr-HR" : "en-US";
    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = lang;
    rec.onresult = (event) => {
      let combined = "";
      for (let i = 0; i < event.results.length; i++) {
        combined += event.results[i][0]?.transcript || "";
      }
      combined = combined.trim();
      if (!combined) return;
      pendingTranscriptRef.current = combined;
      setVoiceStatus(`Heard: “${combined.slice(0, 80)}${combined.length > 80 ? "…" : ""}”`);
      scheduleIngest(combined);
    };
    rec.onerror = () => {
      useBrowserSttRef.current = false;
      setVoiceStatus("Using microphone capture — speak, then tap Stop.");
    };
    rec.onend = () => {
      if (isRecordingRef.current && useBrowserSttRef.current) {
        try {
          rec.start();
        } catch {
          /* noop */
        }
      }
    };
    rec.start();
    speechRef.current = rec;
    return true;
  }, [scheduleIngest]);

  const startPcmCapture = React.useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
    mediaStreamRef.current = stream;
    const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    audioContextRef.current = ctx;
    if (ctx.state === "suspended") await ctx.resume();

    const pushChunk = (pcm: Int16Array) => {
      if (pcm.length) pcmChunksRef.current.push(pcm);
    };

    try {
      await ctx.audioWorklet.addModule(`${window.location.origin}/mic-processor.js`);
      const worklet = new AudioWorkletNode(ctx, "mic-processor", {
        numberOfInputChannels: 1,
        numberOfOutputChannels: 1,
      });
      worklet.port.onmessage = (event) => pushChunk(new Int16Array(event.data));
      const source = ctx.createMediaStreamSource(stream);
      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;
      source.connect(worklet);
      worklet.connect(silentGain);
      silentGain.connect(ctx.destination);
      workletNodeRef.current = worklet;
      silentGainRef.current = silentGain;
    } catch {
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          const sample = Math.max(-1, Math.min(1, input[i]));
          int16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
        }
        pushChunk(int16);
      };
      const source = ctx.createMediaStreamSource(stream);
      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;
      source.connect(processor);
      processor.connect(silentGain);
      silentGain.connect(ctx.destination);
      workletNodeRef.current = processor;
      silentGainRef.current = silentGain;
    }
  }, []);

  const startVoice = async () => {
    if (!voiceContextRef.current) {
      setVoiceStatus("Open the accommodation profile before using voice.");
      return;
    }
    try {
      lastIngestedRef.current = "";
      pendingTranscriptRef.current = "";
      pcmChunksRef.current = [];
      isRecordingRef.current = true;
      setIsRecording(true);
      useBrowserSttRef.current = startSpeechRecognition();
      if (useBrowserSttRef.current) {
        setVoiceStatus("Listening — your words become a profile draft.");
      } else {
        await startPcmCapture();
        setVoiceStatus("Recording — speak a fact, then tap Stop to ingest.");
      }
    } catch {
      void stopVoice();
      setVoiceStatus("Microphone permission is required for voice ingestion.");
    }
  };

  const canUseVoice =
    voiceEnabled &&
    Boolean(voiceContext) &&
    typeof window !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia);

  return (
    <div className="space-y-2 sm:space-y-3">
      {quickReplies.length > 0 && (
        <HorizontalChipScroller>
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => submit(reply)}
              className="shrink-0 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800 hover:bg-blue-100"
            >
              {reply}
            </button>
          ))}
        </HorizontalChipScroller>
      )}
      <div className="flex flex-col gap-2 sm:flex-row">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder={placeholder}
          rows={1}
          className="min-h-14 w-full flex-1 resize-none rounded-2xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 sm:min-h-[52px]"
          disabled={disabled}
        />
        <div className="flex shrink-0 flex-row gap-2 sm:flex-col">
          <Button
            type="button"
            size="sm"
            className="h-10 flex-1 rounded-2xl px-4 sm:h-auto sm:w-auto sm:min-h-10 sm:flex-none"
            aria-label="Send assistant message"
            onClick={() => submit()}
            disabled={disabled || !text.trim()}
          >
            <Send className="h-4 w-4" />
            <span className="ml-1.5 sm:hidden">Send</span>
          </Button>
          <Button
            type="button"
            size="sm"
            variant={isRecording ? "danger" : "outline"}
            className="h-10 flex-1 rounded-2xl px-4 text-sm sm:h-auto sm:min-h-10 sm:flex-none"
            aria-label={isRecording ? "Stop voice capture" : "Capture fact by voice"}
            onClick={isRecording ? () => void stopVoice() : startVoice}
            disabled={!canUseVoice || disabled}
            title={canUseVoice ? "Speak a fact — it becomes a draft to Apply" : "Voice capture unavailable"}
          >
            {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            <span className="ml-1.5">{isRecording ? "Stop" : "Talk"}</span>
          </Button>
        </div>
      </div>
      {voiceStatus && <p className="text-xs text-gray-600">{voiceStatus}</p>}
    </div>
  );
}

declare global {
  interface SpeechRecognitionEvent {
    results: { length: number; [index: number]: { 0: { transcript: string }; isFinal: boolean } };
  }
}
