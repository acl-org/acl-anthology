class PapersPeople < ActiveRecord::Migration
  def change
  	create_table :papers_people, :id => false do |t|
    	t.integer :paper_id
    	t.integer :person_id
  	end
  end
end
