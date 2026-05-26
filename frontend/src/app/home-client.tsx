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
} from "lucide-react";

const contactEmail =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL || "info@syntagent.com";
const contactPhone =
  process.env.NEXT_PUBLIC_CONTACT_PHONE || "+385 98 622 793";

export default function HomeClient() {
  const features = [
    {
      title: "AI Guest Recommendations",
      description:
        "Deliver personalized local guides for every guest — restaurants, wineries, events, and hidden gems tailored to their preferences and your local knowledge.",
      icon: <Bot className="h-7 w-7" />,
      benefits: [
        "Personalized guest experiences",
        "Higher satisfaction ratings",
        "Authentic Croatian insights",
      ],
    },
    {
      title: "Local Business Integration",
      description:
        "Connect guests with restaurants, wineries, OPGs, and local providers — building authentic partnerships across the Kvarner region.",
      icon: <Building2 className="h-7 w-7" />,
      benefits: [
        "Partner with local businesses",
        "Curated authentic experiences",
        "Support local tourism economy",
      ],
    },
    {
      title: "Simple Access Codes",
      description:
        "Generate secure access codes for guest groups. No guest registration required — simple onboarding and preference tracking.",
      icon: <KeyRound className="h-7 w-7" />,
      benefits: ["Simple guest onboarding", "Group preference tracking", "Activity feedback system"],
    },
    {
      title: "Kvarner Region Focus",
      description:
        "Launching in the Kvarner region with plans to expand across the Adriatic — authentic Croatian experiences from Rijeka to the islands.",
      icon: <Compass className="h-7 w-7" />,
      benefits: ["Kvarner pilot program", "Seasonal event integration", "Cultural authenticity"],
    },
  ];

  const testimonials = [
    {
      name: "HostForGuest Beta",
      location: "Coming to Kvarner region",
      quote:
        "We are piloting HostForGuest with accommodation hosts in the Kvarner region. Join the beta program and be among the first to offer AI-powered local guides to your guests.",
      rating: 5,
    },
    {
      name: "AI-Powered Recommendations",
      location: "Powered by Syntagent",
      quote:
        "HostForGuest uses advanced AI to create personalized local experiences for every guest, from wine recommendations to cultural events and hidden gems.",
      rating: 5,
    },
    {
      name: "Kvarner Region Launch",
      location: "Starting Summer 2026",
      quote:
        "Our pilot program launches in the Kvarner region, partnering with local tourism providers to bring authentic Croatian experiences to every guest.",
      rating: 5,
    },
  ];

  return (
    <div className="min-h-screen">
      <HeroSection
        title="AI Local Guide for Your Guests"
        subtitle="HostForGuest — by Syntagent"
        description="Transform your guest experience with AI-powered local recommendations. Help your guests discover authentic restaurants, wineries, events, and hidden gems — all through a simple conversational interface."
        backgroundGradient="from-blue-600 via-teal-600 to-green-600"
        ctaText="Join the Beta"
        ctaHref="/login"
        secondaryCtaText="Learn More"
        secondaryCtaHref="https://syntagent.com"
      >
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center items-center text-white/80">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400 rounded-full"></span>
            <span className="text-sm">AI-Powered Recommendations</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
            <span className="text-sm">Kvarner Region Pilot</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
            <span className="text-sm">Built by Syntagent</span>
          </div>
        </div>
      </HeroSection>

      <FeatureSection
        title="Everything You Need for Premium Hospitality"
        subtitle="AI-powered local guide platform for accommodation hosts and their guests. Built by Syntagent."
        features={features}
        className="bg-white"
      />

      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">How HostForGuest Works</h2>
            <p className="text-xl text-slate-300 max-w-3xl mx-auto">
              Simple, powerful workflow designed for accommodation hosts
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              {
                step: "1",
                title: "Host Onboarding",
                description:
                  "Create your profile with AI assistance, share your local knowledge, and set up your hospitality offering.",
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
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-2xl mx-auto mb-4 shadow-lg">
                    {item.icon}
                  </div>
                  <div className="w-8 h-8 bg-blue-500/30 text-blue-300 rounded-full flex items-center justify-center font-bold text-sm mx-auto mb-3">
                    {item.step}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">{item.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* AI Services & API Keys section */}
      <section className="py-20 bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">AI-Powered Features &amp; API Keys</h2>
            <p className="text-xl text-blue-200 max-w-3xl mx-auto">
              HostForGuest uses AI (OpenAI, Google Gemini) for personalized recommendations, itinerary generation, and smart search
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Option 1 */}
            <Card className="bg-slate-800/80 backdrop-blur border-slate-600/50 hover:border-blue-500 transition-all">
              <CardContent className="p-8">
                <div className="w-14 h-14 bg-gradient-to-br from-green-400 to-emerald-600 rounded-full flex items-center justify-center mb-5">
                  <KeyRound className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Use Your Own API Keys</h3>
                <p className="text-slate-300 text-sm mb-4">
                  Bring your own OpenAI or Google Gemini keys. Full control over usage and costs.
                </p>
                <ul className="space-y-2 text-sm text-slate-300">
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    Add keys in Host Settings &gt; AI Configuration
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    Your keys, your billing, no middleman
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    Works immediately after setup
                  </li>
                </ul>
              </CardContent>
            </Card>

            {/* Option 2 */}
            <Card className="bg-white/10 backdrop-blur border-white/20 hover:border-purple-400 transition-all">
              <CardContent className="p-8">
                <div className="w-14 h-14 bg-gradient-to-br from-purple-400 to-pink-600 rounded-full flex items-center justify-center mb-5">
                  <Sparkles className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Syntagent-Managed Keys</h3>
                <p className="text-slate-300 text-sm mb-4">
                  <span className="inline-block bg-green-500/20 text-green-300 text-xs font-semibold px-2 py-0.5 rounded-full mb-2">3-day free trial</span><br />
                  Subscribe and let us handle the AI infrastructure. No technical setup needed.
                </p>
                <ul className="space-y-2 text-sm text-slate-300">
                  <li className="flex items-start gap-2">
                    <span className="text-purple-400 mt-1">✦</span>
                    No API keys to manage or configure
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-400 mt-1">✦</span>
                    Predictable monthly subscription
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-purple-400 mt-1">✦</span>
                    All AI features included
                  </li>
                </ul>
                <div className="mt-6 pt-4 border-t border-white/10">
                  <p className="text-xs text-slate-400">
                    Contact: {contactEmail} | {contactPhone}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="text-center mt-8">
            <p className="text-blue-300 text-sm">
              New hosts get a <strong className="text-green-300">3-day free trial</strong> of all AI features — no API key needed. After the grace period, add your own keys or subscribe to continue using AI features.
            </p>
            <p className="text-blue-400 text-xs mt-2">
              Guests can always browse local recommendations and content without an API key. AI-powered generation (itineraries, smart search) requires active AI access.
            </p>
          </div>
        </div>
      </section>

      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Join the HostForGuest Beta</h2>
            <p className="text-xl text-gray-600">
              Be among the first hosts to offer AI-powered local guides in the Kvarner region
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
            Ready to Transform Your Guest Experience?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join the HostForGuest beta and offer AI-powered local guides to your guests in the Kvarner region.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-lg px-6 py-3 text-lg font-semibold text-blue-600 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-600 bg-white hover:bg-blue-50"
            >
              Join the Beta
            </Link>
            <Link
              href="/guest/join"
              className="inline-flex items-center justify-center rounded-lg border-2 border-white bg-transparent px-6 py-3 text-lg font-semibold text-white transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-blue-600 hover:bg-white hover:text-blue-600"
            >
              Try guest access
            </Link>
          </div>
          <p className="text-blue-200 text-sm mt-6">
            3-day free trial • No credit card required • Setup in minutes • Powered by Syntagent AI
          </p>
        </div>
      </section>

      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">HostForGuest</h3>
              <p className="text-gray-400 text-sm">
                AI-powered local guide platform for accommodation hosts and their guests. Built by Syntagent.
              </p>
              <p className="mt-3 text-sm">
                <a
                  href="https://syntagent.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Powered by Syntagent →
                </a>
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-3">For Hosts</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>
                  <Link href="/login" className="hover:text-white">
                    Join Beta
                  </Link>
                </li>
                <li>
                  <Link href="/dashboard" className="hover:text-white">
                    Host Dashboard
                  </Link>
                </li>
                <li>
                  <Link href="/onboarding" className="hover:text-white">
                    Get Started
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
              <h4 className="font-semibold mb-3">Regions</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li>Kvarner (Rijeka, Opatija, Krk)</li>
                <li>Istria (Rovinj, Pula)</li>
                <li>Dalmatia (Split, Dubrovnik)</li>
                <li>Expanding across Adriatic</li>
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
                  <MapPin className="h-4 w-4" /> Kvarner, Croatia
                </li>
                <li className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4" /> Built by Syntagent
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
            <p>&copy; 2026 HostForGuest by Syntagent. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
