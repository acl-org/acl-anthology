class RemoveAttachmentAndAttachTypeFromPapers < ActiveRecord::Migration
  def change
    remove_column :papers, :atttachment, :string
    remove_column :papers, :attach_type, :string
  end
end
