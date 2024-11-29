'use client';

import React, { Suspense, lazy, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/authProvider';
import axios from 'axios';
import { ArrowLeft, Eye, EyeOff, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
// import BannerCard from '@/components/banner-card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Loading from '@/components/loading';
const BannerCard = lazy(() => import('@/components/banner-card'));

function SignUpContent() {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
    })
    const [showPassword, setShowPassword] = useState<boolean>(false);
    const [showConfirmPassword, setShowConfirmPassword] =
        useState<boolean>(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();
    const { login } = useAuth();

    const togglePasswordVisibility = (field: 'password' | 'confirmPassword') => {
        if (field == 'password') {
            setShowPassword(!showPassword)
        } else {
            setShowConfirmPassword(!setShowConfirmPassword)
        }
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prevFormData) => ({ ...prevFormData, [name]: value }))
    }

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        console.log(formData)
        setError('');
        setIsLoading(true);

        if (formData.password !== formData.confirmPassword) {
            setError("Passwords don't match");
            setIsLoading(false);
            return;
        }

        try {
            const response = await axios.post(
                `http://localhost:8080/api/signup`,
                {
                    username: formData.username,
                    email: formData.email,
                    password: formData.password,
                },
                {
                    headers: {
                        'Content-Type': 'application/json',
                    }
                }
            );

            if (response.data.status === 'success') {
                toast('User Sign Up successful');
                router.push('/signin');
            }
        } catch (error: any) {
            toast(error.response?.data?.detail || 'An error occurred during sign up');
            setError(
                error.response?.data?.detail || 'An error occurred during sign up'
            );
        } finally {
            setIsLoading(false);
        }
    };

    return (<div className="flex h-full w-full flex-col lg:flex-row">
        <div className="flex flex-1 items-center justify-center p-6 lg:p-12">
            <div className="w-full max-w-[400px] space-y-6">
                <Button variant="ghost" className="mb-4" asChild>
                    <Link href="/">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Link>
                </Button>
                <div className="space-y-2 text-center">
                    <h1 className="text-3xl font-bold">Sign Up</h1>
                    <p className="text-balance text-muted-foreground">
                        Create an account to get started
                    </p>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-1 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                name="username"
                                placeholder="John"
                                required
                                value={formData.username}
                                onChange={handleChange}
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            name="email"
                            type="email"
                            placeholder="m@example.com"
                            required
                            value={formData.email}
                            onChange={handleChange}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                            <Input
                                id="password"
                                name="password"
                                type={showPassword ? 'text' : 'password'}
                                required
                                value={formData.password}
                                onChange={handleChange}
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 top-0 h-full px-3 py-2"
                                onClick={() => togglePasswordVisibility('password')}
                            >
                                {showPassword ? (
                                    <EyeOff className="h-4 w-4" />
                                ) : (
                                    <Eye className="h-4 w-4" />
                                )}
                            </Button>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="confirmPassword">Confirm Password</Label>
                        <div className="relative">
                            <Input
                                id="confirmPassword"
                                name="confirmPassword"
                                type={showConfirmPassword ? 'text' : 'password'}
                                required
                                value={formData.confirmPassword}
                                onChange={handleChange}
                            />
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 top-0 h-full px-3 py-2"
                                onClick={() => togglePasswordVisibility('confirmPassword')}
                            >
                                {showConfirmPassword ? (
                                    <EyeOff className="h-4 w-4" />
                                ) : (
                                    <Eye className="h-4 w-4" />
                                )}
                            </Button>
                        </div>
                    </div>
                    {error && (
                        <Alert variant="destructive">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? 'Creating Account...' : 'Create Account'}
                        {isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin ml-4" />
                        ) : (
                            <></>
                        )}
                    </Button>
                </form>
                <div className="text-center text-sm">
                    Already have an account?{' '}
                    <Link href="/signin" className="underline">
                        Log in
                    </Link>
                </div>
            </div>
        </div>
        <div className="hidden flex-1 lg:flex justify-center items-center bg-muted">
            <BannerCard />
        </div>
    </div>
    );


}

export default function SignUp() {
    return (
        <Suspense fallback={<Loading />}>
            <SignUpContent />
        </Suspense>
    )
}