"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { GuestEVisitorData, GuestEVisitorDataCreate } from "@/lib/api";

// E-Visitor Data Management Modal Components
export const EVisitorDataModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  evisitorData: GuestEVisitorData[];
  onCreateNew: () => void;
  onEdit: (evisitor: GuestEVisitorData) => void;
  onDelete: (evisitorId: string) => void;
  onMarkRegistered: (evisitorId: string, confirmationNumber: string) => void;
}> = ({ isOpen, onClose, evisitorData, onCreateNew, onEdit, onDelete, onMarkRegistered }) => {
  const [showRegistrationModal, setShowRegistrationModal] = useState(false);
  const [selectedEVisitorForRegistration, setSelectedEVisitorForRegistration] = useState<GuestEVisitorData | null>(null);
  const [confirmationNumber, setConfirmationNumber] = useState('');

  if (!isOpen) return null;

  const handleMarkRegistered = () => {
    if (selectedEVisitorForRegistration && confirmationNumber) {
      onMarkRegistered(selectedEVisitorForRegistration.id, confirmationNumber);
      setShowRegistrationModal(false);
      setSelectedEVisitorForRegistration(null);
      setConfirmationNumber('');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">🇭🇷 E-Visitor Data Management</h2>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-gray-600">
              Manage Croatian e-visitor registration data for your guests. This data is required for Croatian tourism compliance.
            </p>
            <Button onClick={onCreateNew} gradient>
              ➕ Add Guest Data
            </Button>
          </div>

          {evisitorData.length === 0 ? (
            <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
              <div className="text-gray-400 mb-2">📋</div>
              <p className="text-gray-500 mb-2">No e-visitor data added yet</p>
              <p className="text-sm text-gray-400">
                Add guest information to comply with Croatian e-visitor registration requirements
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {evisitorData.map((evisitor) => (
                <div key={evisitor.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {evisitor.first_name} {evisitor.last_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {evisitor.nationality} • {evisitor.id_type.toUpperCase()}: {evisitor.id_number}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {evisitor.evisitor_registered ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✅ Registered
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          ⏳ Pending
                        </span>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onEdit(evisitor)}
                      >
                        ✏️ Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onDelete(evisitor.id)}
                      >
                        🗑️ Delete
                      </Button>
                      {!evisitor.evisitor_registered && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setSelectedEVisitorForRegistration(evisitor);
                            setShowRegistrationModal(true);
                          }}
                        >
                          ✅ Mark Registered
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Date of Birth:</span> {new Date(evisitor.date_of_birth).toLocaleDateString()}
                    </div>
                    <div>
                      <span className="font-medium">Stay:</span> {new Date(evisitor.arrival_date).toLocaleDateString()} - {new Date(evisitor.departure_date).toLocaleDateString()}
                    </div>
                    {evisitor.email && (
                      <div>
                        <span className="font-medium">Email:</span> {evisitor.email}
                      </div>
                    )}
                    {evisitor.phone && (
                      <div>
                        <span className="font-medium">Phone:</span> {evisitor.phone}
                      </div>
                    )}
                    {evisitor.evisitor_confirmation_number && (
                      <div className="col-span-2">
                        <span className="font-medium">Confirmation #:</span> {evisitor.evisitor_confirmation_number}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>

        {/* Registration Confirmation Modal */}
        {showRegistrationModal && selectedEVisitorForRegistration && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900">Mark as Registered</h3>
                <Button variant="ghost" onClick={() => setShowRegistrationModal(false)}>✕</Button>
              </div>

              <div className="mb-4">
                <p className="text-gray-600 mb-4">
                  Mark <strong>{selectedEVisitorForRegistration.first_name} {selectedEVisitorForRegistration.last_name}</strong> as registered with Croatian e-visitor system.
                </p>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confirmation Number *
                  </label>
                  <input
                    type="text"
                    value={confirmationNumber}
                    onChange={(e) => setConfirmationNumber(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter e-visitor confirmation number"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setShowRegistrationModal(false)}>
                  Cancel
                </Button>
                <Button 
                  gradient 
                  onClick={handleMarkRegistered}
                  disabled={!confirmationNumber}
                >
                  Mark as Registered
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const CreateEVisitorModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: () => void;
  data: GuestEVisitorDataCreate;
  onChange: (data: GuestEVisitorDataCreate) => void;
  mode: 'create' | 'edit';
}> = ({ isOpen, onClose, onSubmit, data, onChange, mode }) => {
  if (!isOpen) return null;

  const countries = [
    'Germany', 'Austria', 'Switzerland', 'Netherlands', 'Belgium', 'France', 'Italy', 'Spain', 'Portugal',
    'United Kingdom', 'Ireland', 'Denmark', 'Sweden', 'Norway', 'Finland', 'Poland', 'Czech Republic',
    'Slovakia', 'Hungary', 'Slovenia', 'Croatia', 'Serbia', 'Bosnia and Herzegovina', 'Montenegro',
    'United States', 'Canada', 'Australia', 'New Zealand', 'Japan', 'South Korea', 'China', 'India',
    'Brazil', 'Argentina', 'Mexico', 'South Africa', 'Other'
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'Add Guest E-Visitor Data' : 'Edit Guest E-Visitor Data'}
          </h2>
          <Button variant="ghost" onClick={onClose}>✕</Button>
        </div>

        <div className="space-y-6">
          {/* Personal Information */}
          <div className="border-b pb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Personal Information</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  First Name *
                </label>
                <input
                  type="text"
                  value={data.first_name}
                  onChange={(e) => onChange({ ...data, first_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="First name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Last Name *
                </label>
                <input
                  type="text"
                  value={data.last_name}
                  onChange={(e) => onChange({ ...data, last_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Last name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Date of Birth *
                </label>
                <input
                  type="date"
                  value={data.date_of_birth}
                  onChange={(e) => onChange({ ...data, date_of_birth: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nationality *
                </label>
                <select
                  value={data.nationality}
                  onChange={(e) => onChange({ ...data, nationality: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select nationality</option>
                  {countries.map((country) => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* ID Information */}
          <div className="border-b pb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">ID Information</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Type *
                </label>
                <select
                  value={data.id_type}
                  onChange={(e) => onChange({ ...data, id_type: e.target.value as 'passport' | 'id_card' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="passport">Passport</option>
                  <option value="id_card">National ID Card</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Number *
                </label>
                <input
                  type="text"
                  value={data.id_number}
                  onChange={(e) => onChange({ ...data, id_number: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Passport or ID number"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Issuing Country *
                </label>
                <select
                  value={data.id_issuing_country}
                  onChange={(e) => onChange({ ...data, id_issuing_country: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select issuing country</option>
                  {countries.map((country) => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Expiry Date
                </label>
                <input
                  type="date"
                  value={data.id_expiry_date || ''}
                  onChange={(e) => onChange({ ...data, id_expiry_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Address Information */}
          <div className="border-b pb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Address Information (Optional)</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Address Line 1
                </label>
                <input
                  type="text"
                  value={data.address_line1 || ''}
                  onChange={(e) => onChange({ ...data, address_line1: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Street address"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Address Line 2
                </label>
                <input
                  type="text"
                  value={data.address_line2 || ''}
                  onChange={(e) => onChange({ ...data, address_line2: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Apartment, suite, etc."
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    City
                  </label>
                  <input
                    type="text"
                    value={data.city || ''}
                    onChange={(e) => onChange({ ...data, city: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="City"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    State/Province
                  </label>
                  <input
                    type="text"
                    value={data.state_province || ''}
                    onChange={(e) => onChange({ ...data, state_province: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="State or province"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    value={data.postal_code || ''}
                    onChange={(e) => onChange({ ...data, postal_code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Postal code"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Country
                </label>
                <select
                  value={data.country || ''}
                  onChange={(e) => onChange({ ...data, country: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select country</option>
                  {countries.map((country) => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Stay Information */}
          <div className="border-b pb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Stay Information</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Arrival Date *
                </label>
                <input
                  type="date"
                  value={data.arrival_date}
                  onChange={(e) => onChange({ ...data, arrival_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Departure Date *
                </label>
                <input
                  type="date"
                  value={data.departure_date}
                  onChange={(e) => onChange({ ...data, departure_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Contact Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Contact Information (Optional)</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={data.email || ''}
                  onChange={(e) => onChange({ ...data, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Email address"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone
                </label>
                <input
                  type="tel"
                  value={data.phone || ''}
                  onChange={(e) => onChange({ ...data, phone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Phone number"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            gradient 
            onClick={onSubmit} 
            disabled={!data.first_name || !data.last_name || !data.date_of_birth || !data.nationality || !data.id_number || !data.id_issuing_country || !data.arrival_date || !data.departure_date}
          >
            {mode === 'create' ? 'Add Guest Data' : 'Update Guest Data'}
          </Button>
        </div>
      </div>
    </div>
  );
};
