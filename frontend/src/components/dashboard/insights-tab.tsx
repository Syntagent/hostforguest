"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export type RealtimeUpdateItem = {
  id: string;
  title: string;
  content: string;
  created_at: string;
  source?: string;
  description?: string;
};

export const InsightsTab: React.FC<{
  realtimeUpdates: RealtimeUpdateItem[];
  onRefresh: () => void;
}> = ({ realtimeUpdates, onRefresh }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Croatian Tourism Insights 🇭🇷</h2>
        <Button variant="outline" onClick={onRefresh}>
          🔄 Refresh Updates
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="bg-gradient-to-br from-blue-50 to-purple-50">
          <CardHeader>
            <CardTitle>Real-time Updates</CardTitle>
            <CardDescription>
              Latest from Croatian tourism sources (Archon knowledge base &amp; integrations)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {realtimeUpdates.map((update, index) => (
                <div key={`${update.id}-${index}`} className="rounded-lg bg-white p-3 shadow-sm">
                  <p className="text-sm font-medium">{update.title || "Tourism Update"}</p>
                  <p className="mt-1 text-sm text-gray-600">
                    {update.description || "New information from Croatian tourism sources"}
                  </p>
                  <div className="mt-2 text-xs text-gray-500">
                    Source: {update.source || "Croatian Tourism Board"}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-50 to-blue-50">
          <CardHeader>
            <CardTitle>Local Expertise</CardTitle>
            <CardDescription>Your authentic Croatian insights</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="rounded-lg bg-white p-4">
                <h4 className="mb-2 font-medium text-green-700">🌰 Seasonal Highlights</h4>
                <p className="text-sm text-gray-600">
                  Share your knowledge about seasonal events like Marunada (chestnut festival) and
                  cherry season in Lovran.
                </p>
              </div>
              <div className="rounded-lg bg-white p-4">
                <h4 className="mb-2 font-medium text-blue-700">🍽️ Local Cuisine</h4>
                <p className="text-sm text-gray-600">
                  Recommend authentic Istrian dishes and local konobas that guests shouldn&apos;t miss.
                </p>
              </div>
              <div className="rounded-lg bg-white p-4">
                <h4 className="mb-2 font-medium text-purple-700">🏞️ Hidden Gems</h4>
                <p className="text-sm text-gray-600">
                  Share secret spots along the Lungomare or in Učka Nature Park.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
