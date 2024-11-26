import Image from "next/image";


import ChatComponent from "./components/ChatComponent";
export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center">
      <ChatComponent/>
    </div>
  );
}
