'use client';

import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import BannerCard from '@/components/banner-card';
import { ArrowLeft, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useState, FormEvent, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/authProvider';
import axios, { AxiosError } from 'axios';
import { toast } from 'sonner';
import Loading from '@/components/loading';


interface LoginResponse {
    access_token: string
}

interface UserResponse {
    id: number
    email: string
    username: string
}

function SignInContent() {
    const [email, setEmail] = useState<string>('');
    const [username, setUsername] = useState<string>('')
    const [password, setPassword] = useState<string>('');
    const [showPassword, setShowPassword] = useState<boolean>(false);
    const [error, setError] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const router = useRouter();
    const { login } = useAuth();

    const togglePasswordVisibility = () => {
        setShowPassword(!showPassword);
    };


    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        const formData = new FormData()
        formData.append("username", username)
        formData.append("password", password)

        console.log(formData)

        try {
            const response = await axios.post<LoginResponse>("http://localhost:8080/api/login", formData,
                {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                }
            )
            const { access_token } = response.data
            const userResponse = await axios.get<UserResponse>("http://localhost:8080/api/me", {
                headers: { Authorization: `Bearer ${access_token}` },
            })
            const {
                email: userEmail,
                first_name,
                last_name,
                role,
                username
            } = userResponse.data;

            // return
            login(
                access_token, "", email, first_name, last_name
            )

        } catch (error) {
            if (axios.isAxiosError(error)) {
                const axiosError = error as AxiosError<{ detail: string }>;
                setError(
                    axiosError.response?.data?.detail ||
                    'An error occurred during sign in'
                );
            } else {
                setError('An unexpected error occurred');
            }
            toast.error('Sign In failed. Please try again.');
        } finally {
            setIsLoading(false);
        }

    }

    return (

        <div className="flex h-full w-full flex-col lg:flex-row">
            <div className="flex flex-1 items-center justify-center p-6 lg:p-12">
                <div className="w-full max-w-[400px] space-y-6">
                    <Button variant="ghost" className="mb-4" asChild>
                        <Link href="/">
                            <ArrowLeft className="mr-2 h-4 w-4" />
                            Back
                        </Link>
                    </Button>
                    <div className="space-y-2 text-center">
                        <h1 className="text-3xl font-bold">Login</h1>
                        <p className="text-balance text-muted-foreground">
                            Enter your email below to login to your account
                        </p>
                    </div>
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                type="username"
                                placeholder="admin"
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="password">Password</Label>
                            </div>
                            <div className="relative">
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="absolute right-0 top-0 h-full px-3 py-2"
                                    onClick={togglePasswordVisibility}
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                        {error && <p className="text-sm text-red-500">{error}</p>}
                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? (
                                <>
                                    Signing In...
                                    <Loader2 className="h-4 w-4 animate-spin ml-4" />
                                </>
                            ) : (
                                'Login'
                            )}
                        </Button>
                    </form>
                    <div className="text-center text-sm">
                        Don&apos;t have an account?{' '}
                        <Link href="/signup" className="underline">
                            Sign up
                        </Link>
                    </div>
                </div>
            </div>
            {/* <div className="hidden flex-1 lg:flex justify-center items-center bg-muted">
                <BannerCard />
            </div> */}
        </div>
    );
}

export default function SignIn () {
    return (
        <Suspense fallback = {<Loading/>}>
            <SignInContent/>
        </Suspense>
    )
}