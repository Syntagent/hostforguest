import React from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';

/**
 * Test component to verify markdown rendering functionality
 */
export const MarkdownTest: React.FC = () => {
  const sampleContent = `## Restaurant Gardens

Restaurant Gardens is a Culinary in Riva 6, 51000, Rijeka, Croatia, 16km from Lovran, Croatia. Situated in the heart of Rijeka, this restaurant offers a pleasant ambiance with a view of the harbor, making it a popular spot for both locals and tourists to enjoy a meal.

The menu features a wide variety of **Mediterranean and Croatian dishes**, including fresh seafood, grilled meats, and traditional pastas like šurlice from the island of Krk.

### Good to know

* **Access:** The restaurant is easily accessible.
* **Timing:** Open daily from 8 AM to 12 AM, making it a great option for lunch, dinner, or a late-night meal.
* **Budget:** The cost is moderate.
* **Pairing:** Combine your visit with a walk through Rijeka's city center and a coffee at one of the many local cafes.

A visit to Restaurant Gardens offers a delightful culinary excursion and a chance to experience the vibrant city of Rijeka, making it a worthwhile addition to your stay in Lovran.`;

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Markdown Rendering Test</h1>
      
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Sample AI-Generated Content:</h2>
        <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
          <MarkdownRenderer content={sampleContent} />
        </div>
      </div>
      
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Raw Markdown:</h2>
        <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-x-auto">
          {sampleContent}
        </pre>
      </div>
    </div>
  );
};

export default MarkdownTest;
