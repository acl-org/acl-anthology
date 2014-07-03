class Paper < ActiveRecord::Base
	resourcify
	
	belongs_to :volume

	has_and_belongs_to_many :people
	accepts_nested_attributes_for :people

	has_many :revisions, :dependent => :destroy
  	validates_associated :revisions
  	accepts_nested_attributes_for :revisions
	
	#validates :anthology_id, :paper_id, :title, :month, :year, :address, :publisher, :url, presence: true

	#validates :paper_id, uniqueness: {:scope => :anthology_id}

	extend FriendlyId
	friendly_id :slug_candidates, use: [:slugged, :history]

	def slug_candidates
		[
			:title,
			[:title, :anthology_id]
		]
	end

	def should_generate_new_friendly_id?
		title_changed? || slug.blank?
	end
end
