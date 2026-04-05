import React from 'react'
interface ChatComponentProps {
  data: {
    text: string;
  };
}

const ChatComponent: React.FC<ChatComponentProps> = ({ data }) => {
  //console.log('Data in ChatComponent:', data.text);
  return (
    <div>
      <p className='text-white'>{data?.text}</p>
    </div>
  )
}

export default ChatComponent