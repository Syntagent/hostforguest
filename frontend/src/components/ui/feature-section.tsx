"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Feature {
  title: string;
  description: string;
  icon: string | React.ReactNode;
  benefits?: string[];
}

interface FeatureSectionProps {
  title: string;
  subtitle?: string;
  features: Feature[];
  className?: string;
  layout?: "grid" | "list";
}

export const FeatureSection: React.FC<FeatureSectionProps> = ({
  title,
  subtitle,
  features,
  className,
  layout = "grid",
}) => {
  return (
    <section className={cn("py-20 px-4 sm:px-6 lg:px-8", className)}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          className="text-center mb-16"
          initial={false}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true, margin: "-80px" }}
        >
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              {subtitle}
            </p>
          )}
        </motion.div>

        {/* Features */}
        <div
          className={cn(
            layout === "grid"
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
              : "space-y-8"
          )}
        >
          {features.map((feature, index) => (
            <FeatureCard
              key={index}
              feature={feature}
              index={index}
              layout={layout}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

const FeatureCard: React.FC<{
  feature: Feature;
  index: number;
  layout: "grid" | "list";
}> = ({ feature, index, layout }) => {
  return (
    <motion.div
      className={cn(
        "relative p-8 bg-white rounded-xl border border-gray-200 shadow-lg hover:shadow-xl transition-all duration-300",
        "hover:scale-105 hover:-translate-y-1",
        layout === "list" && "flex items-start gap-6"
      )}
      initial={false}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.08 }}
      viewport={{ once: true, margin: "-40px" }}
      whileHover={{ scale: layout === "grid" ? 1.05 : 1.02 }}
    >
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-indigo-50 rounded-xl opacity-0 hover:opacity-100 transition-opacity duration-300" />
      
      {/* Content */}
      <div className="relative z-10 flex-1">
        {/* Icon */}
        <div className={cn(
          "mb-6",
          layout === "list" && "mb-0 flex-shrink-0"
        )}>
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-2xl shadow-lg">
            {typeof feature.icon === 'string' ? feature.icon : feature.icon}
          </div>
        </div>
        
        <div className={layout === "list" ? "flex-1" : ""}>
          {/* Title */}
          <h3 className="text-xl font-semibold text-gray-900 mb-3">
            {feature.title}
          </h3>
          
          {/* Description */}
          <p className="text-gray-600 leading-relaxed mb-4">
            {feature.description}
          </p>
          
          {/* Benefits */}
          {feature.benefits && feature.benefits.length > 0 && (
            <ul className="space-y-2">
              {feature.benefits.map((benefit, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 text-sm text-gray-600"
                >
                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full flex-shrink-0" />
                  {benefit}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </motion.div>
  );
};
