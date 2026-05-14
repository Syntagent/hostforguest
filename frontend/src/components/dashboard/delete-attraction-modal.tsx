"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import type { Attraction } from "@/lib/api";

export const DeleteAttractionModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  attraction: Attraction;
}> = ({ isOpen, onClose, onConfirm, attraction }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Delete Attraction</h2>
          <Button variant="ghost" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="mb-6">
          <p className="mb-4 text-gray-600">
            Are you sure you want to delete <strong>{attraction.name}</strong>?
          </p>
          <p className="text-sm text-gray-500">
            This action cannot be undone. All reviews and recommendations associated with this
            attraction will also be removed.
          </p>
        </div>

        <div className="flex gap-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            Delete Attraction
          </Button>
        </div>
      </div>
    </div>
  );
};
