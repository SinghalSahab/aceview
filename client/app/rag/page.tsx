'use client';
import React, { useState } from "react";

import ChatComponent from "@/components/rag/Chat";
import FileUpload from "@/components/rag/FileUpload";


export default function Home() {
  const [resData, setResData] = useState<any>(null);
  return (
    <div>
      <div className="flex w-screen  min-h-screen">
      <div className="w-[30vw] min-h-screen p-4 flex justify-center items-center">
          <FileUpload className='p-16 mt-10 border border-neutral-200' dataset={setResData}/>
        </div>
        <div className="w-[70vw] min-h-screen border-l-2">
          <ChatComponent data={resData} />
        </div>
      </div>
    </div>
  );
}
