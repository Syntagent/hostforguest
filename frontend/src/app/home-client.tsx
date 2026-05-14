"use client";

import React from "react";
import Link from "next/link";
import { HeroSection } from "@/components/ui/hero-section";
import { FeatureSection } from "@/components/ui/feature-section";
import { Card, CardContent } from "@/components/ui/card";
import {
  Bot,
  Building2,
  Compass,
  HeartHandshake,
  KeyRound,
  Mail,
  MapPin,
  ShieldCheck,
  Sparkles,
  Star,
  Phone,
  Users,
} from "lucide-react";

const contactEmail =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL || "hello@touristguidelocal.hr";
const contactPhone =
  process.env.NEXT_PUBLIC_CONTACT_PHONE || "Available on request";

export default function HomeClient() {
  const features = [
    {
      title: "AI-Powered Recommendations",
      description:
        "Create personalized experiences for your guests with intelligent recommendations based on their preferences and your local knowledge.",
      icon: <Bot className="h-7 w-7" />,
      benefits: [
        "Personalized guest experiences",
        "Higher satisfaction ratings",
        "Authentic Croatian insights",
      ],
    },
    {
      title: "Real-Time Croatian Tourism Data",
      description:
        "Access live updates from Croatian tourism sources to keep your recommendations current and accurate.",
      icon: <Sparkles className="h-7 w-7" />,
      benefits: ["Live tourism updates", "Official event information", "Weather-based suggestions"],
    },
    {
      title: "Easy Guest Management",
      description:
        "Manage your guests with simple access codes, track their preferences, and provide collaborative itinerary planning.",
      icon: <Users className="h-7 w-7" />,
      benefits: ["Simple guest onboarding", "Group preference tracking", "Activity feedback system"],
    },
    {
      title: "Lovran Area Expertise",
      description:
        "Starting with beautiful Lovran and Istria, showcase your local knowledge of Croatian hidden gems and authentic experiences.",
      icon: <Compass className="h-7 w-7" />,
      benefits: ["Local business partnerships", "Seasonal event integration", "Cultural authenticity"],
    },
  ];

  const testimonials = [
    {
      name: "Marija Kovač",
      location: "Villa Adriatic, Lovran",
      quote:
        "TouristGuideLocal transformed how I interact with my guests. They love the personalized recommendations and I've seen a significant increase in satisfaction ratings.",
      rating: 5,
    },
    {
      name: "Petar Jurić",
      location: "Apartment Opatija",
      quote:
        "The AI recommendations are spot-on! My guests appreciate the authentic local experiences, and it's helped me build lasting relationships with them.",
      rating: 5,
    },
    {
      name: "Ana Matić",
      location: "Villa Istria, Rovinj",
      quote:
        "The real-time Croatian tourism data keeps my recommendations fresh. I love how easy it is to create access codes and manage multiple guest groups.",
      rating: 5,
    },
  ];

  return (
    <div className="min-h-screen">
      <HeroSection
        title="Transform Your Croatian Hospitality"
        subtitle="TouristGuideLocal - B2B Platform for Croatian Hosts"
        description="Create exceptional guest experiences with AI-powered local guide services. Connect international tourists with authentic Croatian culture, from Lovran to the entire Croatian coast."
        backgroundGradient="from-blue-600 via-teal-600 to-green-600"
        ctaText="Start Your Host Journey"
        ctaHref="/onboarding"
        secondaryCtaText="Host Login"
        secondaryCtaHref="/login"
      >
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center items-center text-white/80">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400 rounded-full"></span>
            <span className="text-sm">Live Croatian Tourism Data</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
            <span className="text-sm">AI-Powered Recommendations</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
            <span className="text-sm">Authentic Croatian Experiences</span>
          </div>
        </div>
      </HeroSection>

      <FeatureSection
        title="Everything You Need for Premium Hospitality"
        subtitle="Powerful tools designed specifically for Croatian tourist hosts"
        features={features}
        className="bg-white"
      />

      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">How TouristGuideLocal Works</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Simple, powerful workflow designed for Croatian hosts
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              {
                step: "1",
                title: "Host Onboarding",
                description:
                  "Create your profile with AI assistance, share your local knowledge, and set up your Croatian hospitality business.",
                icon: <Building2 className="h-7 w-7" />,
              },
              {
                step: "2",
                title: "Guest Access Codes",
                description:
                  "Generate temporary access codes for your guest groups. Simple, secure, and no registration required for guests.",
                icon: <KeyRound className="h-7 w-7" />,
              },
              {
                step: "3",
                title: "AI Recommendations",
                description:
                  "Our AI creates personalized recommendations based on guest preferences and your authentic local insights.",
                icon: <Sparkles className="h-7 w-7" />,
              },
              {
                step: "4",
                title: "Memorable Experiences",
                description:
                  "Guests enjoy authentic Croatian experiences while you build your reputation as a premium host.",
                icon: <HeartHandshake className="h-7 w-7" />,
              },
            ].map((item, index) => (
              <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-2xl mx-auto mb-4">
                    {item.icon}
                  </div>
                  <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold text-sm mx-auto mb-3">
                    {item.step}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{item.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{item.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Trusted by Croatian Hosts</h2>
            <p className="text-xl text-gray-600">
              Join the growing community of premium Croatian hospitality providers
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center mb-4">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                    ))}
                  </div>
                  <p className="text-gray-700 mb-4 italic">&quot;{testimonial.quote}&quot;</p>
                  <div className="border-t pt-4">
                    <p className="font-semibold text-gray-900">{testimonial.name}</p>
                    <p className="text-sm text-gray-600">{testimonial.location}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
            Ready to Elevate Your Croatian Hospitality?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join Croatian hosts who are creating exceptional guest experiences with AI-powered local guide services.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center rounded-lg px-6 py-3 text-lg font-semibold text-blue-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-600 bg-white hover:bg-blue-50"
            >
              Start Free Onboarding
            </Link>
            <Link
              href="/guest/join"
              className="inline-flex items-center justify-center rounded-lg border-2 border-white bg-transparent px-6 py-3 text-lg font-semibold text-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-600 hover:bg-white hover:text-blue-600"
            >
              Try guest access
            </Link>
          </div>
          <p className="text-blue-200 text-sm mt-6">
            No credit card required • Setup in 5 minutes • Croatian tourism data included
          </p>
        </div>
      </section>

      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">TouristGuideLocal</h3>
              <p className="text-gray-400 text-sm">
                Empowering Croatian hosts with AI-powered local guide services for exceptional guest experiences.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-3">For Hosts</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>
                  <Link href="/onboarding" className="hover:text-white">
                    Get Started
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard" className="hover:text-white">
                    Host Dashboard
                  </Link>
                </li>
                <li>
                  <Link href="/pricing" className="hover:text-white">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="/support" className="hover:text-white">
                    Support
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Croatian Regions</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>Istria (Lovran, Opatija, Rovinj)</li>
                <li>Dalmatia (Split, Dubrovnik)</li>
                <li>Kvarner (Rijeka, Krk)</li>
                <li>Central Croatia (Zagreb)</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Contact</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <Mail className="h-4 w-4" /> {contactEmail}
                </li>
                <li className="flex items-center gap-2">
                  <Phone className="h-4 w-4" /> {contactPhone}
                </li>
                <li className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" /> Lovran, Istria, Croatia
                </li>
                <li className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4" /> Croatian Tourism Certified
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
            <p>&copy; 2024 TouristGuideLocal. All rights reserved. Crafted for modern Croatian hospitality.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
