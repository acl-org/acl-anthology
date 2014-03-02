class Venue < ActiveRecord::Base
	has_many :events
  	validates_associated :events
  	accepts_nested_attributes_for :events

  	extend FriendlyId
	friendly_id :acronym, use: [:slugged, :history]

	def should_generate_new_friendly_id?
		acronym_changed?
	end
end
