class Person < ActiveRecord::Base
	has_and_belongs_to_many :volumes

	has_and_belongs_to_many :papers
	validates_associated :papers

	#validates :first_name, :last_name, presence: true

	#validates_uniqueness_of :last_name, :scope => [:first_name]
	#causes error when seeding data
	#validates :last_name, uniqueness: {:scope => :first_name}
end
