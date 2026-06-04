// AudioWorklet processor for Gemini Live: Float32 mic input -> Int16 PCM chunks.
const BUFFER_SIZE = 4096;

class MicProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(BUFFER_SIZE);
    this.offset = 0;
  }

  process(inputs) {
    const inputBuffer = inputs[0];
    if (!inputBuffer || inputBuffer.length === 0) return true;
    let input = inputBuffer[0];
    for (let ch = 0; ch < inputBuffer.length && (!input || input.length === 0); ch += 1) {
      input = inputBuffer[ch];
    }
    if (!input || input.length === 0) return true;

    for (let i = 0; i < input.length; i += 1) {
      this.buffer[this.offset] = input[i];
      this.offset += 1;
      if (this.offset >= BUFFER_SIZE) {
        const int16 = new Int16Array(BUFFER_SIZE);
        for (let j = 0; j < BUFFER_SIZE; j += 1) {
          const sample = Math.max(-1, Math.min(1, this.buffer[j]));
          int16[j] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
        }
        this.port.postMessage(int16.buffer, [int16.buffer]);
        this.offset = 0;
      }
    }
    return true;
  }
}

registerProcessor("mic-processor", MicProcessor);

