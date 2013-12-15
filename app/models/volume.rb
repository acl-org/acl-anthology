class Volume < ActiveRecord::Base
	has_many :papers
  	validates_associated :papers
  	accepts_nested_attributes_for :papers

  	has_and_belongs_to_many :people
  	validates_associated :people
  	accepts_nested_attributes_for :people

	#validates :volume_id, :title, :month, :year, :address, :publisher, :url, presence: true

	#validates :volume_id, uniqueness: true
end
