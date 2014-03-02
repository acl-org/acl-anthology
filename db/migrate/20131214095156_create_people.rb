class CreatePeople < ActiveRecord::Migration
  def change
    create_table :people do |t|
      t.integer :person_id
      t.string :first_name
      t.string :last_name
      t.string :full_name

      t.timestamps
    end

    add_column :people, :slug, :string
    add_index :people, :slug, unique: true
  end
end
