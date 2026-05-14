"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps
  extends Omit<
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd"
  > {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  gradient?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  iconPosition = "left",
  gradient = false,
  disabled,
  onClick,
  type = "button",
  ...props
}) => {
  const baseClasses =
    "inline-flex items-center justify-center rounded-2xl font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 enabled:hover:-translate-y-0.5 enabled:active:translate-y-px";
  
  const variantClasses = {
    primary: gradient 
      ? "bg-gradient-to-r from-cyan-700 via-sky-700 to-orange-500 text-white hover:from-cyan-800 hover:via-sky-800 hover:to-orange-600 focus:ring-cyan-700 shadow-lg shadow-sky-900/20"
      : "bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary shadow-sm",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80 focus:ring-primary/40",
    outline: "border-2 border-primary/35 bg-white/80 text-primary hover:bg-primary hover:text-primary-foreground focus:ring-primary",
    ghost: "text-primary hover:bg-primary/10 focus:ring-primary/50",
    danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90 focus:ring-destructive",
  };
  
  const sizeClasses = {
    sm: "min-h-10 px-4 py-2 text-sm gap-1.5",
    md: "min-h-11 px-5 py-2.5 text-base gap-2",
    lg: "min-h-12 px-7 py-3 text-lg gap-2.5",
  };

  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        isDisabled && "cursor-not-allowed opacity-50",
        className
      )}
      disabled={isDisabled}
      onClick={onClick}
      {...props}
    >
      {loading && (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
      )}

      {!loading && icon && iconPosition === "left" && (
        <span className="flex-shrink-0">{icon}</span>
      )}

      {!loading && children}

      {!loading && icon && iconPosition === "right" && (
        <span className="flex-shrink-0">{icon}</span>
      )}
    </button>
  );
};
