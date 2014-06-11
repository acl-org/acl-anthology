class Person < ActiveRecord::Base
	resourcify
	
	has_and_belongs_to_many :volumes

	has_and_belongs_to_many :papers
	validates_associated :papers

	#validates :first_name, :last_name, presence: true

	#validates_uniqueness_of :last_name, :scope => [:first_name]
	#causes error when seeding data
	#validates :last_name, uniqueness: {:scope => :first_name}

	extend FriendlyId
	friendly_id :person_slug, use: [:slugged, :history]

	def person_slug
		"#{full_name} #{id}"
	end

	def should_generate_new_friendly_id?
		full_name_changed? || slug.blank?
	end
end
