// "use client";

// import { useEffect, useMemo, useState } from "react";

// export interface ChatConfig {
//   backend?: string;
//   starterQuestions?: string[];
// }

// export function useClientConfig(): ChatConfig {
//   const chatAPI = process.env.NEXT_PUBLIC_CHAT_API;
//   const [config, setConfig] = useState<ChatConfig>();

//   const backendOrigin = useMemo(() => {
//     return chatAPI ? new URL(chatAPI).origin : "";
//   }, [chatAPI]);

//   const configAPI = `${backendOrigin}/api/chat/config`;

//   useEffect(() => {
//     fetch(configAPI)
//       .then((response) => response.json())
//       .then((data) => setConfig({ ...data, chatAPI }))
//       .catch((error) => console.error("Error fetching config", error));
//   }, [chatAPI, configAPI]);

//   return {
//     backend: backendOrigin,
//     starterQuestions: config?.starterQuestions,
//   };
// }

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/app/authProvider'; // Make sure to import useAuth from your AuthContext
import { useRouter } from 'next/navigation';

export interface ChatConfig {
  backend?: string;
  starterQuestions?: string[];
}

export function useClientConfig(): ChatConfig {
  const chatAPI = process.env.NEXT_PUBLIC_CHAT_API;
  const [config, setConfig] = useState<ChatConfig>();
  const { accessToken } = useAuth(); // Get the access token from the auth context
  const router = useRouter();
  
  const backendOrigin = useMemo(() => {
    return chatAPI ? new URL(chatAPI).origin : '';
  }, [chatAPI]);

  const configAPI = `${backendOrigin}/api/chat/config`;

  useEffect(() => {
    // If no access token or no backend origin, skip
    if (!accessToken || !backendOrigin) return;

    const fetchConfig = async () => {
      try {
        const response = await fetch(configAPI, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch configuration');
        }

        const data = await response.json();
        setConfig({ ...data, chatAPI });
      } catch (error) {
        console.error('Error fetching config:', error);
        // router.push('/signin');
      }
    };

    // fetchConfig();
  }, [accessToken, backendOrigin, configAPI, router, chatAPI]);

  return {
    backend: backendOrigin,
    starterQuestions: config?.starterQuestions,
  };
}
