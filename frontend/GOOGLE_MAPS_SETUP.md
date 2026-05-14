# Google Maps Integration Setup

## 🗺️ Setting Up Google Maps API

To enable the interactive map features in the guest dashboard, you need to set up a Google Maps API key.

### 1. Get a Google Maps API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Maps JavaScript API**
   - **Places API**
   - **Geocoding API**
4. Go to "Credentials" and create an API key
5. Restrict the API key to your domain for security

### 2. Configure Environment Variables

Create a `.env.local` file in the frontend directory:

```bash
# Google Maps API Key
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

### 3. Features Enabled

With Google Maps integration, guests can now:

- **Interactive Map View**: See all Croatian attractions on an interactive map
- **Location Markers**: Click on markers to see attraction details
- **Real-time Place Data**: Get live information from Google Places
- **Map Controls**: Zoom, pan, and explore Croatia visually
- **Location Details**: View ratings, photos, and contact information

### 4. Map Features

- **Croatia-focused**: Map is restricted to Croatia for better performance
- **Category Icons**: Different emoji icons for each attraction category
- **Info Windows**: Click markers to see detailed information
- **Responsive Design**: Works on desktop and mobile devices
- **Street View**: Access Street View for selected locations

### 5. Security Notes

- Always restrict your API key to your domain
- Monitor API usage in Google Cloud Console
- Consider setting up billing alerts
- The API key is exposed to the client (required for Maps JavaScript API)

### 6. Troubleshooting

If the map doesn't load:
1. Check that your API key is correct
2. Verify that the required APIs are enabled
3. Check browser console for error messages
4. Ensure the API key has proper restrictions

## 🎯 Benefits

This integration transforms the guest experience from a static list to an interactive, professional tourism platform that:

- Provides visual exploration of Croatian attractions
- Offers real-time place data and photos
- Creates a modern, engaging user interface
- Sets hosts apart from competitors
- Enhances guest engagement and satisfaction
