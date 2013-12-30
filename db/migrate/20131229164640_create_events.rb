class CreateEvents < ActiveRecord::Migration
  def change
    create_table :events do |t|
      t.integer :year
      t.integer :venue_id
      t.string :kind

      t.timestamps
    end
  end
end
