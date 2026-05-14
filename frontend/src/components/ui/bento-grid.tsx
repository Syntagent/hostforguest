"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface BentoGridItem {
  title: string;
  description?: string;
  icon?: string | React.ReactNode;
  /** Optional hero image above the title (e.g. attraction photo). */
  headerImage?: string;
  className?: string;
  content?: React.ReactNode;
  suggestions?: string[];
  category?: string;
  cost?: string;
  authenticity?: string;
  bestTime?: string;
  onClick?: () => void;
}

interface BentoGridProps {
  items: BentoGridItem[];
  className?: string;
}

export const BentoGrid: React.FC<BentoGridProps> = ({
  items,
  className,
}) => {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto",
        className
      )}
    >
      {items.map((item, index) => (
        <BentoGridItem key={index} {...item} index={index} />
      ))}
    </div>
  );
};

const BentoGridItem: React.FC<BentoGridItem & { index: number }> = ({
  title,
  description,
  icon,
  headerImage,
  className,
  content,
  suggestions,
  category,
  cost,
  authenticity,
  bestTime,
  onClick,
  index,
}) => {
  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-xl border border-gray-200 bg-white p-6 shadow-lg transition-all duration-300 group",
        onClick && "cursor-pointer",
        "hover:-translate-y-0.5 hover:shadow-xl",
        className
      )}
      initial={false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
      onClick={onClick}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Background Gradient */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-indigo-50 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="pointer-events-none absolute inset-0 rounded-xl border border-blue-200/0 transition-colors duration-300 group-hover:border-blue-300/60" />
      
      {/* Content */}
      <div className="relative z-10 min-w-0">
        {headerImage ? (
          <div className="-mx-6 -mt-6 mb-4 overflow-hidden rounded-t-xl border-b border-gray-100">
            <img
              src={headerImage}
              alt=""
              className="h-40 w-full object-cover"
              loading="lazy"
            />
          </div>
        ) : null}
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-3">
              {icon && (
                <div className="shrink-0 text-sky-700 [&>svg]:h-5 [&>svg]:w-5">
                  {typeof icon === 'string' ? icon : icon}
                </div>
              )}
              <h3 className="min-w-0 truncate font-semibold text-lg text-gray-900 transition-colors group-hover:text-blue-700">
                {title}
              </h3>
            </div>
            {category && (
              <span className="mt-1 block text-sm text-gray-500 capitalize">
                {category}
              </span>
            )}
          </div>
          
          {authenticity && (
            <span className={cn(
              "ml-3 shrink-0 rounded-full px-2 py-1 text-xs font-medium",
              (authenticity === 'high' || authenticity === 'very_high') && "bg-green-100 text-green-700",
              authenticity === 'medium' && "bg-yellow-100 text-yellow-700",
              authenticity === 'low' && "bg-red-100 text-red-700"
            )}>
              {authenticity} authenticity
            </span>
          )}
        </div>
        
        {/* Description */}
        {description && (
          <p className="text-gray-600 mb-4 leading-relaxed">
            {description}
          </p>
        )}
        
        {/* Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="mb-4">
            <h4 className="font-medium text-gray-800 mb-2">Suggestions:</h4>
            <div className="space-y-2">
              {suggestions.slice(0, 3).map((suggestion, idx) => (
                <div
                  key={idx}
                  className="text-sm text-gray-600 p-2 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  {suggestion}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Content */}
        {content && (
          <div className="mb-4">
            {content}
          </div>
        )}
        
        {/* Footer Info */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          {cost && (
            <span className="flex items-center gap-1">{cost}</span>
          )}
          {bestTime && (
            <span className="flex items-center gap-1">{bestTime}</span>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export { BentoGridItem };
