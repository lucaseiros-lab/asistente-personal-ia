"use client";

import { useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";

interface MessageInputProps {
  onSend: (content: string, inputType: "texto" | "audio") => Promise<void>;
  disabled?: boolean;
}

type RecordingState = "idle" | "recording" | "transcribing";

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function handleSendText(event: React.FormEvent) {
    event.preventDefault();
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    setError(null);
    try {
      await onSend(content, "texto");
      setText("");
    } catch {
      setError("No se pudo enviar el mensaje");
    } finally {
      setSending(false);
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        setRecordingState("transcribing");
        try {
          const { text: transcribed } = await api.transcribeAudio(blob);
          if (transcribed.trim()) {
            await onSend(transcribed.trim(), "audio");
          }
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "No se pudo transcribir el audio");
        } finally {
          setRecordingState("idle");
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecordingState("recording");
    } catch {
      setError("No se pudo acceder al micrófono");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  const micLabel =
    recordingState === "recording"
      ? "Detener grabación"
      : recordingState === "transcribing"
        ? "Transcribiendo…"
        : "Hablar";

  return (
    <div className="border-t border-zinc-800 bg-zinc-950 p-4">
      {error && <p className="mb-2 text-xs text-red-400">{error}</p>}
      <form onSubmit={handleSendText} className="flex items-end gap-2">
        <button
          type="button"
          onClick={recordingState === "recording" ? stopRecording : startRecording}
          disabled={disabled || recordingState === "transcribing"}
          aria-label={micLabel}
          title={micLabel}
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-xl transition disabled:opacity-50 ${
            recordingState === "recording"
              ? "animate-pulse bg-red-600 text-white"
              : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700"
          }`}
        >
          {recordingState === "transcribing" ? "…" : "🎙️"}
        </button>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSendText(e);
            }
          }}
          rows={1}
          placeholder="Escribí un mensaje…"
          disabled={disabled}
          className="max-h-40 flex-1 resize-none rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-indigo-500 disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={disabled || sending || !text.trim()}
          className="h-12 shrink-0 rounded-xl bg-indigo-600 px-5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-40"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
