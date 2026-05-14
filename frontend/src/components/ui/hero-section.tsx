"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface HeroSectionProps {
  title: string;
  subtitle?: string;
  description?: string;
  backgroundGradient?: string;
  ctaText?: string;
  ctaAction?: () => void;
  ctaHref?: string;
  secondaryCtaText?: string;
  secondaryCtaAction?: () => void;
  secondaryCtaHref?: string;
  /** When false, primary/secondary CTAs are hidden (e.g. guest join page). */
  showCTA?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const ctaButtonClass =
  "inline-block px-8 py-4 rounded-lg font-semibold text-lg transition-colors duration-200 text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-transparent";

export const HeroSection: React.FC<HeroSectionProps> = ({
  title,
  subtitle,
  description,
  backgroundGradient = "from-blue-600 via-purple-600 to-indigo-800",
  ctaText,
  ctaAction,
  ctaHref,
  secondaryCtaText,
  secondaryCtaAction,
  secondaryCtaHref,
  showCTA = true,
  className,
  children,
}) => {
  const showPrimary = showCTA && Boolean(ctaText) && (Boolean(ctaHref) || Boolean(ctaAction));
  const showSecondary =
    showCTA && Boolean(secondaryCtaText) && (Boolean(secondaryCtaHref) || Boolean(secondaryCtaAction));

  return (
    <section
      className={cn(
        "relative flex min-h-screen items-center justify-center overflow-hidden",
        `bg-gradient-to-br ${backgroundGradient}`,
        className
      )}
      style={{ backgroundColor: "#0f766e" }}
      aria-labelledby="hero-heading"
    >
      <div className="absolute inset-0 bg-black/20" />
      <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />

      <div
        className="tg-hero-float-a absolute left-10 top-10 h-20 w-20 rounded-full bg-white/10 blur-xl"
        aria-hidden
      />
      <div
        className="tg-hero-float-b absolute bottom-10 right-10 h-32 w-32 rounded-full bg-white/5 blur-xl"
        aria-hidden
      />

      <div className="relative z-10 mx-auto max-w-7xl px-4 text-center sm:px-6 lg:px-8">
        <motion.div
          initial={false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {subtitle && (
            <p className="mb-4 text-lg font-medium text-blue-200 md:text-xl">{subtitle}</p>
          )}

          <h1
            id="hero-heading"
            className="mb-6 text-4xl font-bold leading-tight text-white md:text-6xl lg:text-7xl"
          >
            {title}
          </h1>

          {description && (
            <p className="mx-auto mb-8 max-w-3xl text-xl leading-relaxed text-blue-100 md:text-2xl">
              {description}
            </p>
          )}

          {(showPrimary || showSecondary) && (
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              {showPrimary && ctaText && (
                <>
                  {ctaHref ? (
                    <Link
                      href={ctaHref}
                      className={cn(
                        ctaButtonClass,
                        "bg-white text-blue-600 shadow-lg hover:bg-blue-50 hover:shadow-xl"
                      )}
                    >
                      {ctaText}
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={ctaAction}
                      className={cn(
                        ctaButtonClass,
                        "bg-white text-blue-600 shadow-lg hover:bg-blue-50 hover:shadow-xl"
                      )}
                    >
                      {ctaText}
                    </button>
                  )}
                </>
              )}
              {showSecondary && secondaryCtaText && (
                <>
                  {secondaryCtaHref ? (
                    <Link
                      href={secondaryCtaHref}
                      className={cn(
                        ctaButtonClass,
                        "border-2 border-white text-white hover:bg-white hover:text-blue-600"
                      )}
                    >
                      {secondaryCtaText}
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={secondaryCtaAction}
                      className={cn(
                        ctaButtonClass,
                        "border-2 border-white text-white hover:bg-white hover:text-blue-600"
                      )}
                    >
                      {secondaryCtaText}
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {children && <div className="mt-8">{children}</div>}
        </motion.div>
      </div>
    </section>
  );
};
