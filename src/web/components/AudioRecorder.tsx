'use client';

import { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { transcribeAudio } from '@/lib/api';

interface AudioRecorderProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  onRecordingStateChange?: (isRecording: boolean) => void;
  onTranscribingStateChange?: (isTranscribing: boolean) => void;
}

export default function AudioRecorder({ onTranscription, disabled = false, onRecordingStateChange, onTranscribingStateChange }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' });
        
        stream.getTracks().forEach(track => track.stop());
        await transcribeRecording(audioFile);
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      onRecordingStateChange?.(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Não foi possível acessar o microfone. Verifique as permissões.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      onRecordingStateChange?.(false);
    }
  };

  const transcribeRecording = async (audioFile: File) => {
    try {
      setIsTranscribing(true);
      onTranscribingStateChange?.(true);
      const result = await transcribeAudio(audioFile);
      onTranscription(result.text);
    } catch (error) {
      console.error('Error transcribing audio:', error);
      alert('Erro ao transcrever áudio. Tente novamente.');
    } finally {
      setIsTranscribing(false);
      onTranscribingStateChange?.(false);
    }
  };

  if (disabled) {
    return null;
  }

  return (
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={isTranscribing}
      className={`flex items-center justify-center w-10 h-10 rounded-full transition-all duration-200 ${
        isTranscribing
          ? 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
          : isRecording
          ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse-fast shadow-lg shadow-red-500/30'
          : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400'
      }`}
      title={isRecording ? 'Parar gravação' : 'Gravar mensagem'}
      style={isRecording ? {
        animation: 'pulse-fast 1s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      } : undefined}
    >
      <style jsx>{`
        @keyframes pulse-fast {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.8;
            transform: scale(1.05);
          }
        }
      `}</style>
      {isTranscribing ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : isRecording ? (
        <MicOff className="w-5 h-5" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  );
}
