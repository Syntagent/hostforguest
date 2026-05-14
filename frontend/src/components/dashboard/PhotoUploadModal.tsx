"use client";

import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Attraction } from "@/lib/api";

interface PhotoUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  attraction: Attraction | null;
  onPhotoUpload: (attractionId: string, photos: File[]) => Promise<void>;
}

export const PhotoUploadModal: React.FC<PhotoUploadModalProps> = ({
  isOpen,
  onClose,
  attraction,
  onPhotoUpload
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) setUploadError(null);
  }, [isOpen]);

  const handleFileSelect = (files: FileList | null) => {
    if (files) {
      const maxBytes = 1_500_000;
      const validFiles = Array.from(files).filter(
        (file) => file.type.startsWith("image/") && file.size <= maxBytes
      );
      setUploadError(null);
      setSelectedFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!attraction || selectedFiles.length === 0) return;
    
    setUploading(true);
    setUploadError(null);
    try {
      await onPhotoUpload(attraction.id, selectedFiles);
      setSelectedFiles([]);
      onClose();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Upload failed. Please try again.";
      setUploadError(message);
      console.error("Error uploading photos:", error);
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen || !attraction) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Upload Photos: {attraction.name}
          </h2>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </div>

        <div className="space-y-6">
          {uploadError && (
            <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              {uploadError}
            </p>
          )}
          {/* Upload Area */}
          <Card>
            <CardHeader>
              <CardTitle>Add Photos</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <div className="text-6xl mb-4">📸</div>
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Drop photos here or click to browse
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  Supports JPG, PNG, GIF up to about 1.5MB each (keeps API requests reliable)
                </p>
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  Choose Files
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={(e) => handleFileSelect(e.target.files)}
                  className="hidden"
                />
              </div>
            </CardContent>
          </Card>

          {/* Selected Files Preview */}
          {selectedFiles.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Selected Photos ({selectedFiles.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Preview ${index + 1}`}
                        className="w-full h-32 object-cover rounded-lg"
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => removeFile(index)}
                          className="text-white"
                        >
                          Remove
                        </Button>
                      </div>
                      <div className="mt-2 text-xs text-gray-600 truncate">
                        {file.name}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Upload Progress */}
          {uploading && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  <span className="text-gray-600">Uploading photos...</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <Button variant="outline" onClick={onClose} disabled={uploading}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || uploading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {uploading ? 'Uploading...' : `Upload ${selectedFiles.length} Photo${selectedFiles.length !== 1 ? 's' : ''}`}
          </Button>
        </div>
      </div>
    </div>
  );
};
