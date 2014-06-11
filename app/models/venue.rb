class Venue < ActiveRecord::Base
	resourcify
	
	has_many :events
  	validates_associated :events
  	accepts_nested_attributes_for :events

  	extend FriendlyId
	friendly_id :acronym, use: :slugged

	def should_generate_new_friendly_id?
		new_record? || slug.blank?
	end
end
