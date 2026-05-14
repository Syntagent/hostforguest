# TouristGuideLocal Frontend

Beautiful, modern frontend for the Croatian Tourism Host Platform built with Next.js 15, TypeScript, and Aceternity UI components.

## 🌟 Features

### 🏠 Host Dashboard
- **Comprehensive Analytics**: View guest groups, attractions, and performance metrics
- **Croatian Tourism Integration**: Real-time updates via Archon knowledge base
- **Multi-language Support**: Croatian, English, German, Italian
- **Beautiful UI**: Aceternity components with Croatian coastal theme

### 👥 Guest Interface
- **Access Code System**: Simple, secure guest access without registration
- **Personalized Recommendations**: AI-powered suggestions based on preferences
- **Interactive Itinerary Planning**: Day-by-day trip planning with Google Maps
- **Collaborative Features**: Group voting and shared decision making

### 🚀 Host Onboarding
- **AI-Powered Profile Generation**: Authentic Croatian host profiles
- **Step-by-Step Wizard**: Guided onboarding with progress tracking
- **Local Attraction Discovery**: AI-suggested hidden gems and experiences
- **Beautiful Animations**: Smooth, engaging user experience

## 🛠️ Technology Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom Croatian tourism theme
- **UI Components**: Aceternity UI components
- **Animations**: Framer Motion
- **API Client**: Custom TypeScript API client
- **State Management**: React hooks and context

## 🎨 Design System

### Croatian Tourism Theme
- **Color Palette**: Blue coastal tones, green Istrian landscapes, traditional Croatian colors
- **Typography**: Inter font family for modern readability
- **Components**: Custom Aceternity components adapted for Croatian hospitality
- **Animations**: Smooth transitions and Croatian-themed animations

### Responsive Design
- **Mobile-First**: Optimized for all device sizes
- **Touch-Friendly**: Designed for mobile tourist interactions
- **Fast Loading**: Optimized images and code splitting
- **Offline Ready**: Service worker for poor connectivity areas

## 🚦 Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running TouristGuideLocal backend API

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your API URL

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=TouristGuideLocal
NEXT_PUBLIC_ENABLE_ARCHON_INTEGRATION=true
NEXT_PUBLIC_DEFAULT_REGION=Istria
NEXT_PUBLIC_DEFAULT_LANGUAGE=en
```

## 📱 Pages & Routes

### Public Routes
- `/` - Landing page with Croatian tourism benefits
- `/onboarding` - Host registration and setup wizard
- `/guest/[accessCode]` - Guest interface (no auth required)

### Protected Routes (Host Authentication)
- `/dashboard` - Host dashboard and analytics
- `/dashboard/groups` - Guest group management
- `/dashboard/attractions` - Attraction management
- `/dashboard/settings` - Host settings and preferences

## 🧩 Component Architecture

### Core UI Components (`/components/ui/`)
- `HeroSection` - Beautiful landing sections with gradients
- `BentoGrid` - Masonry-style content grid
- `FeatureSection` - Feature highlights with icons
- `Card` - Flexible card component with hover effects
- `Button` - Animated buttons with loading states

### Feature Components
- `HostDashboard` - Complete host management interface
- `GuestInterface` - Tourist-facing recommendation system
- `HostOnboarding` - Multi-step onboarding wizard
- `AttractionCard` - Croatian attraction display
- `ItineraryPlanner` - Day-by-day trip planning

## 🔌 API Integration

### Backend Connection
- **Base URL**: Configurable via environment variables
- **Authentication**: JWT token-based host authentication
- **Error Handling**: Comprehensive error states and retry logic
- **Type Safety**: Full TypeScript interfaces for all API responses

### Archon Integration
- **Knowledge Base**: Direct queries to Archon for Croatian tourism data
- **Real-time Updates**: Live tourism information and events
- **Smart Recommendations**: AI-powered content suggestions
- **Project Management**: Integration with Archon task tracking

## 🎯 Croatian Tourism Features

### Regional Support
- **Istria**: Lovran, Opatija, Rovinj, Pula
- **Dalmatia**: Split, Dubrovnik, Hvar
- **Kvarner**: Rijeka, Krk, Cres
- **Central Croatia**: Zagreb, Plitvice Lakes

### Cultural Integration
- **Multi-language**: Croatian, English, German, Italian
- **Local Events**: Seasonal festivals (Marunada, Cherry Days)
- **Authentic Experiences**: Traditional konobas, local specialties
- **Croatian Hospitality**: Gostoprimstvo cultural values

### Tourism Data
- **Official Sources**: Croatian Tourism Board integration
- **Real-time Updates**: Live event and attraction information
- **Weather Integration**: Weather-based activity recommendations
- **Seasonal Intelligence**: Time-appropriate suggestions

## 🧪 Testing & Quality

### Code Quality
- **TypeScript**: Full type safety across the application
- **ESLint**: Configured for Next.js and React best practices
- **Prettier**: Consistent code formatting
- **Husky**: Pre-commit hooks for quality assurance

### Performance
- **Next.js Optimization**: Automatic code splitting and optimization
- **Image Optimization**: Next.js Image component for fast loading
- **Bundle Analysis**: Regular bundle size monitoring
- **Lighthouse Scores**: 90+ performance, accessibility, SEO

## 🌍 Internationalization

### Supported Languages
- **Croatian (hr)**: Primary language for local hosts
- **English (en)**: International tourist standard
- **German (de)**: Major tourist demographic
- **Italian (it)**: Regional tourist language

### Implementation
- **Next.js i18n**: Built-in internationalization support
- **Dynamic Loading**: Language files loaded on demand
- **RTL Support**: Ready for Arabic/Hebrew if needed
- **Cultural Adaptation**: Region-specific content and formatting

## 🚀 Deployment

### Production Build
```bash
# Build optimized production bundle
npm run build

# Start production server
npm start
```

### Docker Support
```dockerfile
# Multi-stage build for production
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Setup
- **Development**: `npm run dev` on localhost:3000
- **Staging**: Vercel or similar platform deployment
- **Production**: Croatian hosting with CDN support

## 📊 Analytics & Monitoring

### Host Analytics
- **Guest Engagement**: Track recommendation usage and feedback
- **Performance Metrics**: Response times and satisfaction scores
- **Business Intelligence**: Revenue impact and guest retention
- **Regional Insights**: Tourism trends and seasonal patterns

### Technical Monitoring
- **Error Tracking**: Sentry integration for error monitoring
- **Performance**: Core Web Vitals and user experience metrics
- **API Monitoring**: Backend response times and success rates
- **User Behavior**: Anonymized usage patterns and flow analysis

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with proper TypeScript types
4. Test thoroughly on multiple devices
5. Submit pull request with Croatian tourism context

### Code Standards
- **TypeScript**: Strict mode enabled, no `any` types
- **React**: Functional components with hooks
- **Accessibility**: WCAG 2.1 AA compliance
- **Performance**: Lighthouse score > 90

### Croatian Context
- **Cultural Sensitivity**: Respect for Croatian traditions and values
- **Tourism Accuracy**: Verify all Croatian tourism information
- **Language Quality**: Native Croatian speaker review for translations
- **Local Testing**: Test with actual Croatian hosts and tourists

## 📞 Support

### Documentation
- **Component Storybook**: Interactive component documentation
- **API Documentation**: Full TypeScript interface documentation
- **User Guides**: Host and guest user manuals
- **Video Tutorials**: Croatian and English tutorial videos

### Community
- **Discord**: TouristGuideLocal Croatian Host Community
- **GitHub Issues**: Bug reports and feature requests
- **Croatian Tourism Board**: Official partnership and support
- **Local Meetups**: Croatian host community events

---

**Made with ❤️ in Croatia 🇭🇷 for Croatian Tourism Excellence**