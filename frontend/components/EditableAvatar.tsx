"use client";
import { useState, useRef } from "react";

const AVATAR_PALETTE = [
  "#102a43", "#243b53", "#065f46", "#92400e",
  "#9f1239", "#1e3a5f", "#3f3f46", "#1e40af",
];

function avatarBg(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_PALETTE[Math.abs(h) % AVATAR_PALETTE.length];
}

interface EditableAvatarProps {
  name: string;
  imageUrl?: string | null;
  size?: number;
  editable?: boolean;
  rounded?: "full" | "lg" | "xl";
  onImageChange?: (file: File) => void;
}

export function EditableAvatar({
  name,
  imageUrl,
  size = 40,
  editable = false,
  rounded = "lg",
  onImageChange,
}: EditableAvatarProps) {
  const [preview, setPreview] = useState<string | null>(imageUrl ?? null);
  const inputRef = useRef<HTMLInputElement>(null);

  const bg = avatarBg(name);
  const radiusClass = rounded === "full" ? "rounded-full" : rounded === "xl" ? "rounded-xl" : "rounded-lg";

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    onImageChange?.(file);
  }

  return (
    <div
      className="relative group flex-shrink-0"
      style={{ width: size, height: size }}
    >
      {/* Avatar surface */}
      <div
        className={`w-full h-full ${radiusClass} flex items-center justify-center overflow-hidden shadow-sm`}
        style={{ backgroundColor: preview ? "transparent" : bg }}
      >
        {preview ? (
          <img src={preview} alt={name} className="w-full h-full object-cover" />
        ) : (
          /* Corporate user icon — not initials */
          <svg
            style={{ width: size * 0.52, height: size * 0.52, color: "rgba(255,255,255,0.9)" }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.8}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        )}
      </div>

      {/* Edit overlay (editable only) */}
      {editable && (
        <>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className={`
              absolute inset-0 ${radiusClass}
              bg-black/0 group-hover:bg-black/45
              flex items-center justify-center
              opacity-0 group-hover:opacity-100
              transition-all duration-150 cursor-pointer
            `}
            title="Alterar foto"
          >
            <svg
              style={{ width: size * 0.36, height: size * 0.36 }}
              className="text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="image/svg+xml,image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />
        </>
      )}
    </div>
  );
}
