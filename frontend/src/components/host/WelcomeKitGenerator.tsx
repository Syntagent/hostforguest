"use client";

import React, { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { Printer, Wifi, MapPin, Phone, Download } from "lucide-react";

export const WelcomeKitGenerator: React.FC = () => {
    const { user } = useAuth();
    const printRef = useRef<HTMLDivElement>(null);

    const handlePrint = () => {
        const printContent = printRef.current;
        if (printContent) {
            const originalContents = document.body.innerHTML;
            document.body.innerHTML = printContent.innerHTML;
            window.print();
            document.body.innerHTML = originalContents;
            window.location.reload(); // Reload to restore event listeners
        }
    };

    if (!user) return null;

    return (
        <div className="p-6 max-w-4xl mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Guest Welcome Kit</h1>
                    <p className="text-gray-600">Generate a printable guide for your property</p>
                </div>
                <Button onClick={handlePrint} className="flex items-center gap-2">
                    <Printer className="w-4 h-4" />
                    Print / Save PDF
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Preview Section */}
                <div className="border rounded-lg p-8 bg-white shadow-sm" ref={printRef}>
                    <div className="text-center mb-8">
                        <h2 className="text-4xl font-bold text-gray-900 mb-2">Welcome!</h2>
                        <p className="text-xl text-gray-600">to {user.business_name || "Our Home"}</p>
                    </div>

                    <div className="space-y-8">
                        {/* WiFi Section */}
                        <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
                            <Wifi className="w-8 h-8 text-blue-600 mt-1" />
                            <div>
                                <h3 className="font-semibold text-lg mb-1">Wi-Fi Connection</h3>
                                <p className="text-gray-600">Network: <span className="font-mono font-bold text-gray-900">Guest_WiFi</span></p>
                                <p className="text-gray-600">Password: <span className="font-mono font-bold text-gray-900">welcome2025</span></p>
                            </div>
                        </div>

                        {/* Address Section */}
                        <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
                            <MapPin className="w-8 h-8 text-red-600 mt-1" />
                            <div>
                                <h3 className="font-semibold text-lg mb-1">Address</h3>
                                <p className="text-gray-600">{user.address}</p>
                                <p className="text-gray-600">{user.city}, {user.county}</p>
                            </div>
                        </div>

                        {/* Contact Section */}
                        <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
                            <Phone className="w-8 h-8 text-green-600 mt-1" />
                            <div>
                                <h3 className="font-semibold text-lg mb-1">Emergency Contact</h3>
                                <p className="text-gray-600">Host: {user.full_name}</p>
                                <p className="text-gray-600">Phone: {user.phone || "+385 91 234 5678"}</p>
                            </div>
                        </div>

                        {/* QR Code Section */}
                        <div className="text-center mt-8 pt-8 border-t border-gray-200">
                            <p className="text-sm text-gray-500 mb-4">Scan to access your digital guide & recommendations</p>
                            <div className="w-48 h-48 bg-gray-200 mx-auto rounded-lg flex items-center justify-center mb-4">
                                <span className="text-gray-400">QR Code Placeholder</span>
                            </div>
                            <p className="font-mono text-sm text-blue-600">app.touristguide.hr/guest/join</p>
                        </div>
                    </div>

                    <div className="mt-12 text-center text-sm text-gray-400">
                        <p>We hope you have a wonderful stay!</p>
                    </div>
                </div>

                {/* Settings Section */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Customization</CardTitle>
                            <CardDescription>Customize what appears on your welcome kit</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Wi-Fi Network Name</label>
                                <input type="text" className="w-full p-2 border rounded-md" placeholder="e.g. Apartment_Guest" />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Wi-Fi Password</label>
                                <input type="text" className="w-full p-2 border rounded-md" placeholder="e.g. summer2025" />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Custom Message</label>
                                <textarea className="w-full p-2 border rounded-md h-24" placeholder="Add a personal welcome note..." />
                            </div>
                            <Button className="w-full">Update Preview</Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};
