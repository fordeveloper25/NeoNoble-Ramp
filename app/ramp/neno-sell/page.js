'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function SellNenoPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [tokens, setTokens] = useState('');
  const [userWallet, setUserWallet] = useState('');
  const [payoutDestination, setPayoutDestination] = useState('');
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [session, setSession] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('user_token');
    const userData = localStorage.getItem('user_data');

    if (!token || !userData) {
      router.push('/auth');
      return;
    }

    setUser(JSON.parse(userData));
  }, [router]);

  useEffect(() => {
    if (tokens && parseFloat(tokens) > 0) {
      fetchQuote();
    } else {
      setQuote(null);
    }
  }, [tokens]);

  const fetchQuote = async () => {
    try {
      const token = localStorage.getItem('user_token');
      const response = await fetch('/api/ui-ramp-offramp-quote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          token: 'NENO',
          chain: 'BSC',
          tokens: parseFloat(tokens),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch quote');
      }

      const data = await response.json();
      setQuote(data);
    } catch (err) {
      console.error('Quote error:', err);
    }
  };

  const handleConfirm = async () => {
    if (!userWallet) {
      setError('Please enter your BSC wallet address');
      return;
    }

    if (!payoutDestination) {
      setError('Please enter your IBAN for payout');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('user_token');
      const response = await fetch('/api/ui-ramp-offramp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          token: 'NENO',
          chain: 'BSC',
          tokens: parseFloat(tokens),
          userWallet,
          payoutDestination,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to create transaction');
      }

      const data = await response.json();
      setSession(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user_token');
    localStorage.removeItem('user_data');
    router.push('/auth');
  };

  if (!user) {
    return (
      <div className=\"min-h-screen bg-gray-50 flex items-center justify-center\">
        <div className=\"animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600\"></div>
      </div>
    );
  }

  if (session) {
    return (
      <div className=\"min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100\">
        <header className=\"bg-white/80 backdrop-blur border-b\">
          <div className=\"container mx-auto px-4 py-4\">
            <div className=\"flex items-center justify-between\">
              <Link href=\"/ramp\" className=\"flex items-center space-x-3\">
                <div className=\"bg-purple-600 text-white p-2 rounded-lg\">
                  <svg className=\"w-6 h-6\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">
                    <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M13 10V3L4 14h7v7l9-11h-7z\" />
                  </svg>
                </div>
                <div>
                  <h1 className=\"text-xl font-bold text-gray-900\">NeoNoble Ramp</h1>
                </div>
              </Link>
              <Button variant=\"outline\" size=\"sm\" onClick={handleLogout}>
                Sign Out
              </Button>
            </div>
          </div>
        </header>

        <main className=\"container mx-auto px-4 py-12 max-w-2xl\">
          <Card className=\"text-center\">
            <CardHeader>
              <div className=\"w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4\">
                <svg className=\"w-8 h-8 text-orange-600\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">
                  <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M5 13l4 4L19 7\" />
                </svg>
              </div>
              <CardTitle className=\"text-2xl text-orange-600\">Transaction Created!</CardTitle>
              <CardDescription>Your NENO sell order has been created</CardDescription>
            </CardHeader>
            <CardContent className=\"space-y-6\">
              <div className=\"bg-gray-50 rounded-lg p-6 space-y-4\">
                <div>
                  <p className=\"text-sm text-gray-500\">Session ID</p>
                  <p className=\"font-mono text-sm mt-1\">{session.sessionId}</p>
                </div>
                <div>
                  <p className=\"text-sm text-gray-500\">Status</p>
                  <p className=\"font-semibold mt-1\">{session.status}</p>
                </div>
                <div className=\"pt-4 border-t\">
                  <div className=\"grid grid-cols-2 gap-4 text-sm\">
                    <div>
                      <p className=\"text-gray-500\">Tokens Sold</p>
                      <p className=\"font-semibold\">{session.details.tokens} NENO</p>
                    </div>
                    <div>
                      <p className=\"text-gray-500\">You Receive</p>
                      <p className=\"font-semibold\">€{session.details.amountFiat.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className=\"text-gray-500\">Fee</p>
                      <p className=\"font-semibold\">€{session.details.feeBase}</p>
                    </div>
                    <div>
                      <p className=\"text-gray-500\">Rate</p>
                      <p className=\"font-semibold\">€{session.details.rate.toLocaleString()}</p>
                    </div>
                  </div>
                  <div className=\"mt-4 pt-4 border-t\">
                    <p className=\"text-sm text-gray-500\">Payout Destination</p>
                    <p className=\"font-mono text-sm mt-1\">{session.details.payoutDestination}</p>
                  </div>
                </div>
              </div>

              <Alert>
                <AlertDescription>
                  <strong>Note:</strong> This is a MOCKED payment flow for MVP purposes. In production, the payout would be processed through a payment provider.
                </AlertDescription>
              </Alert>

              <div className=\"space-y-3\">
                <Button className=\"w-full\" onClick={() => router.push('/ramp')}>
                  Return to Home
                </Button>
                <Button variant=\"outline\" className=\"w-full\" onClick={() => window.location.reload()}>
                  Make Another Sale
                </Button>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className=\"min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-100\">
      <header className=\"bg-white/80 backdrop-blur border-b\">
        <div className=\"container mx-auto px-4 py-4\">
          <div className=\"flex items-center justify-between\">
            <Link href=\"/ramp\" className=\"flex items-center space-x-3\">
              <div className=\"bg-purple-600 text-white p-2 rounded-lg\">
                <svg className=\"w-6 h-6\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">
                  <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M13 10V3L4 14h7v7l9-11h-7z\" />
                </svg>
              </div>
              <div>
                <h1 className=\"text-xl font-bold text-gray-900\">NeoNoble Ramp</h1>
                <p className=\"text-xs text-gray-500\">{user.email}</p>
              </div>
            </Link>
            <Button variant=\"outline\" size=\"sm\" onClick={handleLogout}>
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className=\"container mx-auto px-4 py-12 max-w-2xl\">
        <div className=\"mb-6\">
          <Link href=\"/ramp\">
            <Button variant=\"ghost\" size=\"sm\">
              <svg className=\"w-4 h-4 mr-2\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">
                <path strokeLinecap=\"round\" strokeLinejoin=\"round\" strokeWidth={2} d=\"M15 19l-7-7 7-7\" />
              </svg>
              Back
            </Button>
          </Link>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className=\"text-2xl\">Sell NENO</CardTitle>
            <CardDescription>Convert NENO tokens to EUR</CardDescription>
          </CardHeader>
          <CardContent className=\"space-y-6\">
            {error && (
              <Alert variant=\"destructive\">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className=\"bg-orange-50 border border-orange-200 rounded-lg p-4\">
              <div className=\"flex items-center justify-between\">
                <span className=\"text-sm text-orange-800\">Current Rate</span>
                <span className=\"text-lg font-bold text-orange-900\">1 NENO = €10,000</span>
              </div>
            </div>

            <div className=\"space-y-4\">
              <div className=\"space-y-2\">
                <Label htmlFor=\"tokens\">Amount (NENO)</Label>
                <Input
                  id=\"tokens\"
                  type=\"number\"
                  placeholder=\"1.0\"
                  value={tokens}
                  onChange={(e) => setTokens(e.target.value)}
                  min=\"0.000001\"
                  step=\"0.000001\"
                />
                <p className=\"text-xs text-gray-500\">Enter the amount of NENO you want to sell</p>
              </div>

              <div className=\"space-y-2\">
                <Label htmlFor=\"wallet\">BSC Wallet Address</Label>
                <Input
                  id=\"wallet\"
                  type=\"text\"
                  placeholder=\"0x...\"
                  value={userWallet}
                  onChange={(e) => setUserWallet(e.target.value)}
                />
                <p className=\"text-xs text-gray-500\">Your wallet address where NENO will be sent from</p>
              </div>

              <div className=\"space-y-2\">
                <Label htmlFor=\"iban\">IBAN (Payout Destination)</Label>
                <Input
                  id=\"iban\"
                  type=\"text\"
                  placeholder=\"DE89370400440532013000\"
                  value={payoutDestination}
                  onChange={(e) => setPayoutDestination(e.target.value)}
                />
                <p className=\"text-xs text-gray-500\">Your IBAN where EUR will be sent</p>
              </div>
            </div>

            {quote && (
              <div className=\"bg-gray-50 rounded-lg p-6 space-y-4\">
                <h3 className=\"font-semibold text-gray-900\">Transaction Summary</h3>
                <div className=\"space-y-3\">
                  <div className=\"flex justify-between text-sm\">
                    <span className=\"text-gray-600\">You sell</span>
                    <span className=\"font-semibold\">{quote.tokens} NENO</span>
                  </div>
                  <div className=\"flex justify-between text-sm\">
                    <span className=\"text-gray-600\">Gross amount</span>
                    <span className=\"font-semibold\">€{quote.amountFiat.toLocaleString()}</span>
                  </div>
                  <div className=\"flex justify-between text-sm\">
                    <span className=\"text-gray-600\">Fee (1%)</span>
                    <span className=\"font-semibold\">€{quote.feeBase}</span>
                  </div>
                  <div className=\"border-t pt-3 flex justify-between\">
                    <span className=\"font-medium text-gray-900\">You receive</span>
                    <span className=\"font-bold text-lg text-orange-600\">€{(quote.amountFiat - quote.feeBase).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            )}

            <Button
              className=\"w-full\"
              size=\"lg\"
              onClick={handleConfirm}
              disabled={!tokens || !userWallet || !payoutDestination || !quote || loading}
            >
              {loading ? 'Processing...' : 'Confirm Sale'}
            </Button>

            <p className=\"text-xs text-center text-gray-500\">
              By clicking Confirm, you agree to the terms and conditions
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
