'use client';

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Modal, Button, Input } from '@/components/ui';

interface ChatTypeEditModalProps {
  open: boolean;
  onClose: () => void;
  chatType?: {
    id: string;
    name: string;
    description?: string;
    tags?: string[];
    is_public: boolean;
  };
  onSave: (data: {
    name: string;
    description?: string;
    tags: string[];
    is_public: boolean;
  }) => Promise<void>;
  loading?: boolean;
}

export default function ChatTypeEditModal({
  open,
  onClose,
  chatType,
  onSave,
  loading = false
}: ChatTypeEditModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [isPublic, setIsPublic] = useState(true);

  useEffect(() => {
    if (chatType) {
      setName(chatType.name);
      setDescription(chatType.description || '');
      setTags(chatType.tags || []);
      setIsPublic(chatType.is_public);
      setTagInput('');
    }
  }, [chatType, open]);

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag) && tags.length < 15) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const handleSave = async () => {
    await onSave({
      name,
      description,
      tags,
      is_public: isPublic
    });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={chatType ? 'Editar Tipo de Chat' : 'Novo Tipo de Chat'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleSave} loading={loading}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Nome
          </label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nome do tipo de chat"
            disabled={loading}
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Descrição
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descrição do tipo de chat"
            disabled={loading}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 disabled:opacity-50 disabled:cursor-not-allowed"
            rows={3}
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Tags ({tags.length}/15)
          </label>
          <div className="space-y-2">
            {/* Tag Input */}
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                placeholder="Adicionar tag (máx 50 caracteres)"
                disabled={loading || tags.length >= 15}
                maxLength={50}
              />
              <Button
                onClick={handleAddTag}
                disabled={loading || !tagInput.trim() || tags.length >= 15}
                variant="secondary"
              >
                Adicionar
              </Button>
            </div>

            {/* Tags Display */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 p-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300 text-sm font-medium"
                  >
                    #{tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      disabled={loading}
                      className="text-brand-600 dark:text-brand-400 hover:text-brand-800 dark:hover:text-brand-200 disabled:opacity-50"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Public/Private */}
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              disabled={loading}
              className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-brand-600 dark:text-brand-400 focus:ring-brand-500 dark:focus:ring-brand-400"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Público
            </span>
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {isPublic ? 'Qualquer pessoa pode ver e usar este tipo de chat' : 'Apenas você pode ver e usar este tipo de chat'}
          </p>
        </div>
      </div>
    </Modal>
  );
}
