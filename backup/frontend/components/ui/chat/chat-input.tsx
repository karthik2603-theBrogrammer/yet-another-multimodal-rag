'use client';
import React, { useRef, useEffect, ChangeEvent } from 'react';
import { JSONValue } from 'ai';
import { Button } from '../button';
import { DocumentPreview } from '../document-preview';
import FileUploader from '../file-uploader';
import { Textarea } from '../textarea';
import UploadImagePreview from '../upload-image-preview';
import { ChatHandler } from './chat.interface';
import { useFile } from './hooks/use-file';
import { CornerRightUp, SendHorizontal } from 'lucide-react';

const ALLOWED_EXTENSIONS = ['pdf', 'txt', 'docx'];

export default function ChatInput(
  props: Pick<
    ChatHandler,
    | 'isLoading'
    | 'input'
    | 'onFileUpload'
    | 'onFileError'
    | 'handleSubmit'
    | 'handleInputChange'
    | 'messages'
    | 'setInput'
    | 'append'
  > & {
    requestParams?: any;
  }
) {
  const {
    imageUrl,
    setImageUrl,
    uploadFile,
    files,
    removeDoc,
    reset,
    getAnnotations,
  } = useFile();

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const lines = scrollHeight / 20; // Assuming 20px per line
      const newHeight = Math.min(lines, 10) * 20;
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [props.input]);

  const handleSubmitWithAnnotations = (
    e: React.FormEvent<HTMLFormElement>,
    annotations: JSONValue[] | undefined
  ) => {
    e.preventDefault();
    props.append!({
      content: props.input,
      role: 'user',
      createdAt: new Date(),
      annotations,
    });
    props.setInput!('');
  };

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const annotations = getAnnotations();
    if (annotations.length) {
      handleSubmitWithAnnotations(e, annotations);
      return reset();
    }
    props.handleSubmit(e);
  };

  const handleUploadFile = async (file: File) => {
    if (imageUrl || files.length > 0) {
      alert('You can only upload one file at a time.');
      return;
    }
    try {
      await uploadFile(file, props.requestParams);
      props.onFileUpload?.(file);
    } catch (error: any) {
      props.onFileError?.(error.message);
    }
  };

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    props.handleInputChange(e as any);
  };

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-3xl p-2 shadow-md shadow-black/10 space-y-4 shrink-0 border-2 border-slate-500/10 bg-background"
    >
      {imageUrl && (
        <UploadImagePreview url={imageUrl} onRemove={() => setImageUrl(null)} />
      )}
      {files.length > 0 && (
        <div className="flex gap-4 w-full overflow-auto py-2">
          {files.map((file) => (
            <DocumentPreview
              key={file.id}
              file={file}
              onRemove={() => removeDoc(file)}
            />
          ))}
        </div>
      )}
      <div className="flex w-full items-end justify-between gap-4 ">
        <Textarea
          ref={textareaRef}
          name="message"
          placeholder="Type a message"
          // className="flex-1 overflow-y-auto resize-none rounded-2xl bg-transparent"
          className="flex-1 resize-none rounded-2xl bg-transparent focus:outline-none focus:ring-0 text-base"
          rows={1}
          value={props.input}
          onChange={handleInputChange}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSubmit(e as any);
            }
          }}
          style={{
            minHeight: '30px',
            maxHeight: '200px',
            overflow: 'hidden',
            border: 'none',
            boxShadow: 'none',
          }}
        />
        {/* <FileUploader
          onFileUpload={handleUploadFile}
          onFileError={props.onFileError}
          config={{
            allowedExtensions: ALLOWED_EXTENSIONS,
            disabled: props.isLoading,
          }}
        /> */}
        <Button
          type="submit"
          disabled={props.isLoading || !props.input.trim()}
          className="w-fit h-fit rounded-2xl"
        >
          <CornerRightUp className="w-5 h-5 font-bold" />
        </Button>
      </div>
    </form>
  );
}
