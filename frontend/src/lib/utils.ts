import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: Date | string): string {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

export function formatCurrency(amount: number, currency: string = 'EUR'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount)
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w ]+/g, '')
    .replace(/ +/g, '-')
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

/** True if lat/lng are finite WGS84 values and not the common 0,0 placeholder. */
export function isPlausibleGpsLatLng(lat: unknown, lng: unknown): boolean {
  const a = typeof lat === "number" ? lat : lat != null && lat !== "" ? Number(lat) : NaN;
  const b = typeof lng === "number" ? lng : lng != null && lng !== "" ? Number(lng) : NaN;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  if (Math.abs(a) < 1e-6 && Math.abs(b) < 1e-6) return false;
  if (a < -90 || a > 90 || b < -180 || b > 180) return false;
  return true;
}
