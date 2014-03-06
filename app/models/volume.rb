class Volume < ActiveRecord::Base
	resourcify
	
	has_and_belongs_to_many :sigs
	accepts_nested_attributes_for :sigs
	has_and_belongs_to_many :events
	accepts_nested_attributes_for :events

	has_many :papers, :dependent => :destroy
  	validates_associated :papers
  	accepts_nested_attributes_for :papers

  	has_and_belongs_to_many :people
  	validates_associated :people
  	accepts_nested_attributes_for :people

	#validates :anthology_id, :title, :month, :year, :address, :publisher, :url, presence: true

	#validates :anthology_id, uniqueness: true

	extend FriendlyId
	friendly_id :title, use: [:slugged, :history]

	def should_generate_new_friendly_id?
		title_changed?
	end
end
