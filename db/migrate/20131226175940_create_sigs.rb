class CreateSigs < ActiveRecord::Migration
  def change
    create_table :sigs do |t|
      t.string :name
      t.string :sigid
      t.string :url

      t.timestamps
    end

    add_column :sigs, :slug, :string
    add_index :sigs, :slug, unique: true
  end
end
