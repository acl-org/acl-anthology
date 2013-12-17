class Paper < ActiveRecord::Base
	belongs_to :volume

	has_and_belongs_to_many :people
	accepts_nested_attributes_for :people
	
	#validates :anthology_id, :paper_id, :title, :month, :year, :address, :publisher, :url, presence: true

	#validates :paper_id, uniqueness: {:scope => :anthology_id}
end
