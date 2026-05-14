"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Attraction } from "@/lib/api";

interface AttractionAnalytics {
  views: number;
  recommendations: number;
  average_rating: number;
  review_count: number;
  guest_feedback: Array<{
    rating: number;
    comment: string;
    created_at: string;
  }>;
}

interface AttractionAnalyticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  attraction: Attraction | null;
}

export const AttractionAnalyticsModal: React.FC<AttractionAnalyticsModalProps> = ({
  isOpen,
  onClose,
  attraction
}) => {
  const [analytics, setAnalytics] = useState<AttractionAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && attraction) {
      loadAnalytics();
    }
  }, [isOpen, attraction]);

  const loadAnalytics = async () => {
    if (!attraction) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const { attractionsApi } = await import('@/lib/api');
      const response = await attractionsApi.getAnalytics(attraction.id);
      
      if (response.success && response.data) {
        setAnalytics(response.data);
      } else {
        setError('Failed to load analytics data');
      }
    } catch (error) {
      console.error('Error loading analytics:', error);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !attraction) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Analytics: {attraction.name}
          </h2>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading analytics...</p>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadAnalytics}>Retry</Button>
          </div>
        ) : analytics ? (
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
                <CardContent className="p-4">
                  <div className="text-2xl font-bold text-blue-600">{analytics.views}</div>
                  <div className="text-sm text-gray-600">Total Views</div>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-green-50 to-green-100">
                <CardContent className="p-4">
                  <div className="text-2xl font-bold text-green-600">{analytics.recommendations}</div>
                  <div className="text-sm text-gray-600">Recommendations</div>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100">
                <CardContent className="p-4">
                  <div className="text-2xl font-bold text-yellow-600">
                    {analytics.average_rating.toFixed(1)}
                  </div>
                  <div className="text-sm text-gray-600">Average Rating</div>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-purple-50 to-purple-100">
                <CardContent className="p-4">
                  <div className="text-2xl font-bold text-purple-600">{analytics.review_count}</div>
                  <div className="text-sm text-gray-600">Reviews</div>
                </CardContent>
              </Card>
            </div>

            {/* Guest Feedback */}
            <Card>
              <CardHeader>
                <CardTitle>Guest Feedback</CardTitle>
              </CardHeader>
              <CardContent>
                {analytics.guest_feedback.length > 0 ? (
                  <div className="space-y-4">
                    {analytics.guest_feedback.map((feedback, index) => (
                      <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                        <div className="flex items-center gap-2 mb-2">
                          <div className="flex">
                            {[...Array(5)].map((_, i) => (
                              <span key={i} className={i < feedback.rating ? "text-yellow-500" : "text-gray-300"}>
                                ⭐
                              </span>
                            ))}
                          </div>
                          <span className="text-sm text-gray-500">
                            {new Date(feedback.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-gray-700">{feedback.comment}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">
                    No guest feedback yet. Encourage your guests to leave reviews!
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Performance Insights */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Insights</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Engagement Rate</span>
                    <span className="text-blue-600 font-semibold">
                      {analytics.views > 0 ? ((analytics.recommendations / analytics.views) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Satisfaction Score</span>
                    <span className="text-green-600 font-semibold">
                      {analytics.average_rating > 0 ? (analytics.average_rating / 5 * 100).toFixed(0) : 0}%
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="font-medium">Review Rate</span>
                    <span className="text-purple-600 font-semibold">
                      {analytics.recommendations > 0 ? ((analytics.review_count / analytics.recommendations) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500">No analytics data available</p>
          </div>
        )}

        <div className="flex justify-end mt-6">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
