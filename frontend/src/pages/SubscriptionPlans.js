/**
 * Subscription Plans Page
 * Displays available subscription plans and allows users to subscribe
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Check, Crown, Zap, Code, Building, Loader2,
  ArrowRight, Star, Shield, AlertCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const PLAN_ICONS = {
  free: Zap,
  pro_trader: Crown,
  premium: Star,
  developer_basic: Code,
  developer_pro: Code,
  enterprise: Building,
};

const PLAN_COLORS = {
  free: 'from-gray-500 to-gray-600',
  pro_trader: 'from-blue-500 to-cyan-500',
  premium: 'from-purple-500 to-pink-500',
  developer_basic: 'from-green-500 to-emerald-500',
  developer_pro: 'from-orange-500 to-amber-500',
  enterprise: 'from-red-500 to-rose-500',
};

export default function SubscriptionPlans() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(false);
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [error, setError] = useState('');

  // Get token from localStorage
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch plans
      const plansRes = await fetch(`${BACKEND_URL}/api/subscriptions/plans/list`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const plansData = await plansRes.json();
      setPlans(plansData.plans || []);

      // Fetch current subscription
      const subRes = await fetch(`${BACKEND_URL}/api/subscriptions/my-subscription`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (subRes.ok) {
        const subData = await subRes.json();
        setCurrentSubscription(subData);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (planId) => {
    setSubscribing(true);
    setError('');

    try {
      const response = await fetch(`${BACKEND_URL}/api/subscriptions/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          plan_id: planId,
          billing_cycle: billingCycle
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Errore nella sottoscrizione');
      }

      // Refresh data
      await fetchData();
      
    } catch (err) {
      setError(err.message);
    } finally {
      setSubscribing(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('Sei sicuro di voler cancellare il tuo abbonamento?')) return;

    try {
      const response = await fetch(`${BACKEND_URL}/api/subscriptions/cancel`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        await fetchData();
      }
    } catch (error) {
      console.error('Error cancelling:', error);
    }
  };

  // Group plans by type
  const userPlans = plans.filter(p => p.plan_type === 'user');
  const developerPlans = plans.filter(p => p.plan_type === 'developer');
  const enterprisePlans = plans.filter(p => p.plan_type === 'enterprise');

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 py-8 text-center">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
            Scegli il tuo Piano
          </h1>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Sblocca funzionalità premium, riduci le commissioni e accedi all'infrastruttura completa di NeoNoble Ramp
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Error */}
        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Current Subscription */}
        {currentSubscription && (
          <div className="mb-8 bg-purple-500/10 border border-purple-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm mb-1">Il tuo piano attuale</p>
                <h3 className="text-xl font-bold text-white">{currentSubscription.plan_name}</h3>
                <p className="text-gray-400 text-sm mt-1">
                  Scade il {new Date(currentSubscription.current_period_end).toLocaleDateString('it-IT')}
                </p>
              </div>
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
              >
                Cancella
              </button>
            </div>
          </div>
        )}

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <span className={`text-sm ${billingCycle === 'monthly' ? 'text-white' : 'text-gray-400'}`}>
            Mensile
          </span>
          <button
            onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
            className={`relative w-14 h-7 rounded-full transition-colors ${
              billingCycle === 'yearly' ? 'bg-purple-500' : 'bg-gray-700'
            }`}
          >
            <div className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${
              billingCycle === 'yearly' ? 'translate-x-8' : 'translate-x-1'
            }`} />
          </button>
          <span className={`text-sm ${billingCycle === 'yearly' ? 'text-white' : 'text-gray-400'}`}>
            Annuale
            <span className="ml-1 text-green-400 text-xs">-17%</span>
          </span>
        </div>

        {/* User Plans */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
            <Crown className="w-5 h-5 text-purple-400" />
            Piani Trading
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {userPlans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                billingCycle={billingCycle}
                isCurrentPlan={currentSubscription?.plan_id === plan.id}
                onSubscribe={() => handleSubscribe(plan.id)}
                subscribing={subscribing}
              />
            ))}
          </div>
        </section>

        {/* Developer Plans */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
            <Code className="w-5 h-5 text-green-400" />
            Piani Developer
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {developerPlans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                billingCycle={billingCycle}
                isCurrentPlan={currentSubscription?.plan_id === plan.id}
                onSubscribe={() => handleSubscribe(plan.id)}
                subscribing={subscribing}
              />
            ))}
          </div>
        </section>

        {/* Enterprise */}
        {enterprisePlans.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Building className="w-5 h-5 text-red-400" />
              Enterprise
            </h2>
            <div className="grid grid-cols-1 gap-6">
              {enterprisePlans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  billingCycle={billingCycle}
                  isCurrentPlan={currentSubscription?.plan_id === plan.id}
                  onSubscribe={() => handleSubscribe(plan.id)}
                  subscribing={subscribing}
                  featured
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function PlanCard({ plan, billingCycle, isCurrentPlan, onSubscribe, subscribing, featured = false }) {
  const Icon = PLAN_ICONS[plan.code] || Shield;
  const gradient = PLAN_COLORS[plan.code] || 'from-purple-500 to-pink-500';
  const price = billingCycle === 'monthly' ? plan.price_monthly : plan.price_yearly;
  const period = billingCycle === 'monthly' ? '/mese' : '/anno';

  // Parse features
  const featureList = Object.entries(plan.features || {}).map(([key, value]) => {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    if (typeof value === 'boolean') {
      return { label, enabled: value };
    } else if (value === -1) {
      return { label: `${label}: Illimitato`, enabled: true };
    } else {
      return { label: `${label}: ${value.toLocaleString()}`, enabled: true };
    }
  }).filter(f => f.enabled);

  return (
    <div className={`relative bg-gray-900 border rounded-2xl overflow-hidden ${
      isCurrentPlan 
        ? 'border-purple-500 ring-2 ring-purple-500/20' 
        : featured 
          ? 'border-gray-700 bg-gradient-to-br from-gray-900 to-gray-800'
          : 'border-gray-800 hover:border-gray-700'
    }`}>
      {isCurrentPlan && (
        <div className="absolute top-0 right-0 bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
          ATTIVO
        </div>
      )}

      <div className={`p-6 bg-gradient-to-r ${gradient} bg-opacity-10`}>
        <div className="flex items-center gap-3 mb-2">
          <div className={`p-2 rounded-lg bg-gradient-to-r ${gradient}`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-xl font-bold text-white">{plan.name}</h3>
        </div>
        <p className="text-gray-400 text-sm">{plan.description}</p>
      </div>

      <div className="p-6">
        <div className="mb-6">
          <span className="text-4xl font-bold text-white">
            €{price.toLocaleString()}
          </span>
          <span className="text-gray-400">{period}</span>
        </div>

        <ul className="space-y-3 mb-6">
          {plan.trading_fee_discount > 0 && (
            <li className="flex items-center gap-2 text-sm">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              <span className="text-gray-300">
                {(plan.trading_fee_discount * 100).toFixed(0)}% sconto commissioni
              </span>
            </li>
          )}
          {plan.max_api_keys > 0 && (
            <li className="flex items-center gap-2 text-sm">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              <span className="text-gray-300">
                {plan.max_api_keys === -1 ? 'API Keys illimitate' : `${plan.max_api_keys} API Keys`}
              </span>
            </li>
          )}
          {plan.max_tokens_created > 0 && (
            <li className="flex items-center gap-2 text-sm">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              <span className="text-gray-300">
                {plan.max_tokens_created === -1 ? 'Token illimitati' : `${plan.max_tokens_created} Token`}
              </span>
            </li>
          )}
          {featureList.slice(0, 4).map((feature, idx) => (
            <li key={idx} className="flex items-center gap-2 text-sm">
              <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
              <span className="text-gray-300">{feature.label}</span>
            </li>
          ))}
        </ul>

        <button
          onClick={onSubscribe}
          disabled={subscribing || isCurrentPlan || price === 0}
          className={`w-full py-3 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${
            isCurrentPlan
              ? 'bg-gray-800 text-gray-400 cursor-default'
              : price === 0
                ? 'bg-gray-800 text-gray-400'
                : `bg-gradient-to-r ${gradient} text-white hover:opacity-90`
          }`}
          data-testid={`subscribe-${plan.code}`}
        >
          {subscribing ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : isCurrentPlan ? (
            'Piano Attivo'
          ) : price === 0 ? (
            'Piano Attuale'
          ) : (
            <>
              Sottoscrivi
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
