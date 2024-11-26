"use client"

import React, { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { PlaceholdersAndVanishInput } from '@/components/ui/placeholders-and-vanish-input';
import { FlipWords } from '@/components/ui/flip-words';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/authProvider';
import Ripple from '@/components/magicui/ripple';
import AnimatedGradientText from '@/components/magicui/animated-gradient-text';
import { cn } from '@/lib/utils';
import { ChevronRight } from 'lucide-react';
import Image from 'next/image';
import { siteConfig } from '@/config/site';
import Link from 'next/link';


export default function Home() {
  const { theme } = useTheme();
  const [inputValue, setInputValue] = useState<string>('');
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const [isAnimating, setIsAnimating] = useState<boolean>(false);

  const words = ["better", "cute", "beautiful", "modern"];
  const placeholders = [
    'Hello there how are you doing',
    'Ask me anything about ....jdjdjddjdj!',
  ];
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };
  const onSubmit = (e : React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsAnimating(true)

    setTimeout(() => {
      if(isAuthenticated) {
        console.log("Authenticated User, pushing to the chat page...")
        router.push(`/chat?query=${encodeURIComponent(inputValue)}`);
      }else{
        router.push("/signin")
      }
    }, 1500)
  }
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <FlipWords words={words} /> <br />
      <PlaceholdersAndVanishInput
        placeholders={placeholders}
        onChange={handleChange}
        onSubmit={onSubmit}
        value={inputValue}
        setValue={setInputValue}
      />
    </div>
  );
}



