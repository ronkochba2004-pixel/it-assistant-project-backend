BEGIN;

--------------------------------------------------
-- DELETE CASCADE CHAIN
-- companies -> users -> chats -> messages -> message_images
--------------------------------------------------

-- When a company is deleted, delete all its users
ALTER TABLE public.users
  DROP CONSTRAINT IF EXISTS users_company_id_fkey;

ALTER TABLE public.users
  ADD CONSTRAINT users_company_id_fkey
  FOREIGN KEY (company_id)
  REFERENCES public.companies(company_id)
  ON DELETE CASCADE;

-- When a user is deleted, delete all their chats
ALTER TABLE public.chats
  DROP CONSTRAINT IF EXISTS chats_user_id_fkey;

ALTER TABLE public.chats
  ADD CONSTRAINT chats_user_id_fkey
  FOREIGN KEY (user_id)
  REFERENCES public.users(user_id)
  ON DELETE CASCADE;

-- When a chat is deleted, delete all its messages
ALTER TABLE public.messages
  DROP CONSTRAINT IF EXISTS messages_chat_id_fkey;

ALTER TABLE public.messages
  ADD CONSTRAINT messages_chat_id_fkey
  FOREIGN KEY (chat_id)
  REFERENCES public.chats(chat_id)
  ON DELETE CASCADE;

-- When a message is deleted, delete all its images
ALTER TABLE public.message_images
  DROP CONSTRAINT IF EXISTS message_images_message_id_fkey;

ALTER TABLE public.message_images
  ADD CONSTRAINT message_images_message_id_fkey
  FOREIGN KEY (message_id)
  REFERENCES public.messages(message_id)
  ON DELETE CASCADE;

--------------------------------------------------
-- BUSINESS CONSTRAINTS
--------------------------------------------------

-- Ensure user email is unique
ALTER TABLE public.users
  ADD CONSTRAINT users_email_unique UNIQUE (email);

-- Ensure image position is between 0 and 4
ALTER TABLE public.message_images
  ADD CONSTRAINT message_images_position_check
  CHECK (position BETWEEN 0 AND 4);

--Sets the time to now
ALTER TABLE public.companies
ALTER COLUMN created_at SET DEFAULT NOW();


COMMIT;
