"use client";
import Image from 'next/image';
import React, { useCallback, useEffect, useState } from 'react';
import { useDropzone ,FileRejection } from 'react-dropzone';
import CloseIcon from '@mui/icons-material/Close';
import UploadFileIcon from '@mui/icons-material/UploadFile';

type FileWithPreview = File & { preview: string };


function MyDropzone({className,dataset }: {className?: string; dataset: (data:any) => void}) {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [rejected, setRejected] = useState<FileRejection[]>([])
  
  const onDrop = useCallback((acceptedFiles:File[], rejectedFiles:FileRejection[]) => {
    if (acceptedFiles?.length) {
      setFiles(previousFiles => [
        ...previousFiles,
        ...acceptedFiles.map(file =>
          Object.assign(file, { preview: URL.createObjectURL(file) })
        )
      ])
    }

    if (rejectedFiles?.length) {
      setRejected(previousFiles => [...previousFiles, ...rejectedFiles])
    }
  }, [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 10485760, // 10MB
    multiple: false
   });

  useEffect(() => {
    // Revoke the data uris to avoid memory leaks
    return () => files.forEach(file => URL.revokeObjectURL(file.preview))
  }, [files])

  const removeFile = (name: string) => {
    setFiles(files => files.filter(file => file.name !== name))
  }

  const removeRejected = (name:string) => {
    setRejected(files => files.filter(({ file }) => file.name !== name))
  }

  useEffect(() => { 
   
    if (files.length > 0) {
      console.log('Accepted Files:', files);
  
      const formData = new FormData();
      formData.append('file', files[0]); // Assuming only one file is allowed
  
      fetch("http://localhost:8080/api/upload", {
        method: "POST",
        body: formData,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error('Failed to upload file');
          }
          return response.json();
        })
        .then((data) => {
          console.log('File uploaded successfully:', data);
          dataset(data);
        })
        .catch((error) => {
          console.error('Error uploading file:', error);
        });
    }
  },[files])
  return (
    <form>
    <div
      {...getRootProps()}
      
    >
      <input {...getInputProps({
        className: className || ''
      })} />
      {isDragActive ? (
        <p>Drop the files here ...</p>
      ) : (
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-neutral-300 rounded-md p-10 cursor-pointer hover:border-secondary-400 transition-colors text-center">
  <UploadFileIcon className="w-32 h-32 text-neutral-400 mb-4" /> 
  <p className="text-lg text-neutral-600">
    Drag 'n' drop a file here, or click to select
  </p>
</div>

      )}
    </div>
   {/* Accepted files */}
   <h3 className='title text-lg font-semibold text-neutral-600 mt-10 border-b pb-3'>
          Accepted Files
        </h3>
        <ul className='mt-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-10'>
          {files.map(file => (
            <li key={file.name} className='relative h-32 rounded-md shadow-lg'>
              <Image
                src={file.preview}
                alt={file.name}
                width={100}
                height={100}
                onLoad={() => {
                  URL.revokeObjectURL(file.preview)
                }}
                className='h-full w-full object-contain rounded-md'
              />
              <button
                type='button'
                title={`Remove ${file.name}`}
                className='w-7 h-7 border border-secondary-400 bg-secondary-400 rounded-full flex justify-center items-center absolute -top-3 -right-3 hover:bg-white transition-colors'
                onClick={() => removeFile(file.name)}
              >
                <CloseIcon className='w-5 h-5 fill-white hover:fill-secondary-400 transition-colors' />
              </button>
              <p className='mt-2 text-neutral-500 text-[12px] font-medium'>
                {file.name}
              </p>
            </li>
          ))}
        </ul>

        {/* Rejected Files */}
        <h3 className='title text-lg font-semibold text-neutral-600 mt-24 border-b pb-3'>
          Rejected Files
        </h3>
        <ul className='mt-6 flex flex-col'>
          {rejected.map(({ file, errors }) => (
            <li key={file.name} className='flex items-start justify-between'>
              <div>
                <p className='mt-2 text-neutral-500 text-sm font-medium'>
                  {file.name}
                </p>
                <ul className='text-[12px] text-red-400'>
                  {errors.map(error => (
                    <li key={error.code}>{error.message}</li>
                  ))}
                </ul>
              </div>
              <button
                type='button'
                className='mt-1 py-1 text-[12px] uppercase tracking-wider font-bold text-neutral-500 border border-secondary-400 rounded-md px-3 hover:bg-secondary-400 hover:text-white transition-colors'
                onClick={() => removeRejected(file.name)}
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      
    </form>
  );
  
}

export default MyDropzone;
