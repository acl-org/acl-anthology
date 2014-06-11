class Sig < ActiveRecord::Base
	resourcify
	
	has_and_belongs_to_many :volumes
  	#validates_associated :volumes
  	accepts_nested_attributes_for :volumes
  	
  	extend FriendlyId
	friendly_id :sigid, use: :slugged

	def should_generate_new_friendly_id?
		new_record? || slug.blank?
	end
end
