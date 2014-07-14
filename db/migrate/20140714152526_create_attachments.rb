class CreateAttachments < ActiveRecord::Migration
  def change
    create_table :attachments do |t|
      t.string :name
      t.string :attach_type
      t.boolean :internal
      t.text :url
      t.references :paper, index: true

      t.timestamps
    end
  end
end
