class CreateVenues < ActiveRecord::Migration
  def change
    create_table :venues do |t|
      t.string :acronym
      t.string :name
      t.string :venue_type

      t.timestamps
    end
  end
end
