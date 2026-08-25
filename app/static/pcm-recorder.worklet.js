/*
 * Raw PCM capture for ElevenLabs Scribe.
 *
 * MediaRecorder only produces webm/opus, and the realtime transcription socket
 * accepts pcm_* or ulaw_8000 only. So the microphone is read frame by frame
 * here, downsampled to the socket's rate, and converted to signed 16-bit.
 *
 * Frames arrive every 128 samples, which is far too small to send individually.
 * They are accumulated into roughly 50ms blocks: small enough that the final
 * block after the spacebar is released is negligible, large enough that the
 * socket is not flooded with tiny messages.
 */

const TARGET_BLOCK_MS = 50;

class PcmRecorder extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const { targetSampleRate = 16000 } = options?.processorOptions || {};
    this.targetSampleRate = targetSampleRate;
    // sampleRate is the AudioWorkletGlobalScope's hardware rate, typically
    // 48000. Scribe is told the target rate, so resample rather than lie.
    this.ratio = sampleRate / targetSampleRate;
    this.blockSize = Math.round((targetSampleRate * TARGET_BLOCK_MS) / 1000);
    this.buffer = new Int16Array(this.blockSize);
    this.filled = 0;
    this.sourceOffset = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    // Walk the source at a fractional step so any hardware rate maps onto the
    // target rate. sourceOffset carries the remainder across frames, which
    // keeps the output continuous instead of clicking at every boundary.
    let position = this.sourceOffset;
    while (position < channel.length) {
      const sample = channel[Math.floor(position)];
      // Clamp before scaling: a value slightly outside [-1, 1] would otherwise
      // wrap to the opposite polarity and appear as a loud click.
      const clamped = Math.max(-1, Math.min(1, sample));
      this.buffer[this.filled++] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
      if (this.filled === this.blockSize) {
        // Post a copy: the buffer is reused immediately for the next block.
        this.port.postMessage(this.buffer.slice(0));
        this.filled = 0;
      }
      position += this.ratio;
    }
    this.sourceOffset = position - channel.length;
    return true;
  }
}

registerProcessor("pcm-recorder", PcmRecorder);
