"use client";

import React from "react";
import { Mic, MicOff, Send } from "lucide-react";
import { Button } from "@/components/ui/button";

type AgentComposerProps = {
  disabled?: boolean;
  quickReplies: string[];
  voiceEnabled?: boolean;
  onSend: (message: string) => void;
};

const DEFAULT_OUTPUT_SAMPLE_RATE = 24000;
const PLAYBACK_TAIL_SUPPRESSION_MS = 120;

function getWsUrl(token: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/onboarding/accommodation/voice/stream?token=${encodeURIComponent(token)}`;
}

function getSampleRateFromMimeType(mimeType?: string) {
  const match = /rate=(\d+)/i.exec(mimeType || "");
  return match ? parseInt(match[1], 10) : DEFAULT_OUTPUT_SAMPLE_RATE;
}

export function AgentComposer({ disabled, quickReplies, voiceEnabled = true, onSend }: AgentComposerProps) {
  const [text, setText] = React.useState("");
  const [voiceStatus, setVoiceStatus] = React.useState<string | null>(null);
  const [isRecording, setIsRecording] = React.useState(false);
  const wsRef = React.useRef<WebSocket | null>(null);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const playbackContextRef = React.useRef<AudioContext | null>(null);
  const mediaStreamRef = React.useRef<MediaStream | null>(null);
  const workletNodeRef = React.useRef<AudioNode | null>(null);
  const silentGainRef = React.useRef<GainNode | null>(null);
  const nextPlayTimeRef = React.useRef(0);
  const activeSourcesRef = React.useRef<AudioBufferSourceNode[]>([]);
  const suppressMicUntilRef = React.useRef(0);

  const submit = (value = text) => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  const clearPlaybackQueue = React.useCallback(() => {
    for (const source of activeSourcesRef.current) {
      try {
        source.stop();
      } catch {
        /* noop */
      }
    }
    activeSourcesRef.current = [];
    nextPlayTimeRef.current = playbackContextRef.current ? playbackContextRef.current.currentTime + 0.01 : 0;
  }, []);

  const isAssistantPlaybackActive = React.useCallback(() => {
    const ctx = playbackContextRef.current;
    if (!ctx) return false;
    return activeSourcesRef.current.length > 0 || nextPlayTimeRef.current > ctx.currentTime + 0.05;
  }, []);

  const stopVoice = React.useCallback(() => {
    clearPlaybackQueue();
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    silentGainRef.current?.disconnect();
    silentGainRef.current = null;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    void playbackContextRef.current?.close();
    playbackContextRef.current = null;
    setIsRecording(false);
    setVoiceStatus(null);
  }, [clearPlaybackQueue]);

  React.useEffect(() => stopVoice, [stopVoice]);

  const playAudioChunk = React.useCallback(async (base64Audio: string, mimeType?: string) => {
    const ctx = playbackContextRef.current;
    if (!base64Audio || !ctx) return;
    if (ctx.state === "suspended") await ctx.resume();
    const binaryStr = window.atob(base64Audio);
    const len = (binaryStr.length >> 1) << 1;
    if (len <= 0) return;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i);
    const sampleCount = len >> 1;
    const float32 = new Float32Array(sampleCount);
    const view = new DataView(bytes.buffer);
    for (let i = 0; i < sampleCount; i++) {
      float32[i] = view.getInt16(i * 2, true) / 32768;
    }
    const audioBuffer = ctx.createBuffer(1, sampleCount, getSampleRateFromMimeType(mimeType));
    audioBuffer.getChannelData(0).set(float32);
    const src = ctx.createBufferSource();
    src.buffer = audioBuffer;
    src.connect(ctx.destination);
    activeSourcesRef.current.push(src);
    src.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter((item) => item !== src);
    };
    const start = nextPlayTimeRef.current < ctx.currentTime ? ctx.currentTime + 0.01 : nextPlayTimeRef.current;
    const end = start + audioBuffer.duration;
    suppressMicUntilRef.current = Math.max(
      suppressMicUntilRef.current,
      performance.now() + Math.max(0, end - ctx.currentTime) * 1000 + PLAYBACK_TAIL_SUPPRESSION_MS,
    );
    src.start(start);
    nextPlayTimeRef.current = end;
  }, []);

  const startVoice = async () => {
    const token = localStorage.getItem("session_token");
    if (!token) {
      setVoiceStatus("Login session required for voice.");
      return;
    }
    try {
      setVoiceStatus("Connecting voice...");
      playbackContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: DEFAULT_OUTPUT_SAMPLE_RATE,
      });
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      const ws = new WebSocket(getWsUrl(token));
      wsRef.current = ws;
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "session_ready") setVoiceStatus("Listening. Speak naturally.");
        if (data.type === "audio_chunk") {
          setVoiceStatus("Assistant speaking...");
          void playAudioChunk(data.data, data.mime_type);
        }
        if (data.type === "interrupted") {
          clearPlaybackQueue();
          setVoiceStatus("Listening to your new question...");
        }
        if (data.type === "turn_complete") setVoiceStatus("Ready for the next fact.");
      };
      ws.onerror = () => setVoiceStatus("Voice server is unavailable.");
      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error("WebSocket failed"));
      });

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      mediaStreamRef.current = stream;
      const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = ctx;
      if (ctx.state === "suspended") await ctx.resume();
      const sendChunk = (pcmInt16Array: Int16Array) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        if (isAssistantPlaybackActive() || performance.now() < suppressMicUntilRef.current) return;
        const bytes = new Uint8Array(pcmInt16Array.buffer);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        wsRef.current.send(JSON.stringify({ type: "audio_chunk", data: btoa(binary), sample_rate: ctx.sampleRate }));
      };
      try {
        await ctx.audioWorklet.addModule(`${window.location.origin}/mic-processor.js`);
        const worklet = new AudioWorkletNode(ctx, "mic-processor", {
          numberOfInputChannels: 1,
          numberOfOutputChannels: 1,
        });
        worklet.port.onmessage = (event) => sendChunk(new Int16Array(event.data));
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
          sendChunk(int16);
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
      setIsRecording(true);
      setVoiceStatus("Listening. Share one accommodation fact at a time.");
    } catch {
      stopVoice();
      setVoiceStatus("Voice is unavailable or microphone permission was denied.");
    }
  };

  const canUseVoice =
    voiceEnabled &&
    typeof window !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    Boolean(window.AudioContext || window.webkitAudioContext);

  return (
    <div className="space-y-3">
      {quickReplies.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              onClick={() => submit(reply)}
              className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800 hover:bg-blue-100"
            >
              {reply}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder="Tell the assistant one important fact about your stay..."
          rows={2}
          className="min-h-[52px] flex-1 rounded-2xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={disabled}
        />
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            size="sm"
            aria-label="Send assistant message"
            onClick={() => submit()}
            disabled={disabled || !text.trim()}
          >
            <Send className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant={isRecording ? "danger" : "outline"}
            aria-label={isRecording ? "Stop voice assistant" : "Start voice assistant"}
            onClick={isRecording ? stopVoice : startVoice}
            disabled={!canUseVoice}
            title={canUseVoice ? "Talk to the assistant" : "Voice is not available in this browser"}
          >
            {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      {voiceStatus && <p className="text-xs text-gray-600">{voiceStatus}</p>}
    </div>
  );
}

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext;
  }
}

