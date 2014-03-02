class Sig < ActiveRecord::Base
	has_and_belongs_to_many :volumes
  	#validates_associated :volumes
  	accepts_nested_attributes_for :volumes
  	
  	extend FriendlyId
	friendly_id :sigid, use: [:slugged, :history]

	def should_generate_new_friendly_id?
		sigid_changed?
	end
end
