/**
 * Web3 Context Provider for NeoNoble Ramp
 * Manages wallet connections across the application
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { WagmiProvider, useAccount, useConnect, useDisconnect, useBalance, useChainId, useSwitchChain } from 'wagmi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { wagmiConfig, chainMetadata, supportedChains } from '../config/web3Config';

// Create Query Client for React Query
const queryClient = new QueryClient();

// Web3 Context
const Web3Context = createContext(null);

// Inner provider that uses wagmi hooks
function Web3ContextInner({ children }) {
  const { address, isConnected, isConnecting, connector } = useAccount();
  const { connect, connectors, isPending, error: connectError } = useConnect();
  const { disconnect } = useDisconnect();
  const chainId = useChainId();
  const { switchChain } = useSwitchChain();
  
  const { data: balance } = useBalance({
    address: address,
    watch: true,
  });

  const [walletState, setWalletState] = useState({
    isModalOpen: false,
    error: null,
  });

  // Get chain info
  const currentChain = chainMetadata[chainId] || { name: 'Unknown', symbol: '?', icon: '❓' };

  // Connect wallet function
  const connectWallet = useCallback(async (connectorId) => {
    try {
      setWalletState(prev => ({ ...prev, error: null }));
      const selectedConnector = connectors.find(c => 
        c.id === connectorId || 
        c.name.toLowerCase().includes(connectorId.toLowerCase())
      );
      
      if (selectedConnector) {
        connect({ connector: selectedConnector });
      } else {
        // Default to first available connector
        connect({ connector: connectors[0] });
      }
    } catch (err) {
      setWalletState(prev => ({ ...prev, error: err.message }));
    }
  }, [connect, connectors]);

  // Disconnect wallet
  const disconnectWallet = useCallback(() => {
    disconnect();
    setWalletState(prev => ({ ...prev, error: null }));
  }, [disconnect]);

  // Switch chain
  const changeChain = useCallback(async (newChainId) => {
    try {
      if (switchChain) {
        switchChain({ chainId: newChainId });
      }
    } catch (err) {
      setWalletState(prev => ({ ...prev, error: err.message }));
    }
  }, [switchChain]);

  // Open/close wallet modal
  const openWalletModal = () => setWalletState(prev => ({ ...prev, isModalOpen: true }));
  const closeWalletModal = () => setWalletState(prev => ({ ...prev, isModalOpen: false }));

  // Format address for display
  const formatAddress = (addr) => {
    if (!addr) return '';
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  const value = {
    // Connection state
    address,
    isConnected,
    isConnecting: isConnecting || isPending,
    connector,
    
    // Chain info
    chainId,
    currentChain,
    supportedChains,
    chainMetadata,
    
    // Balance
    balance: balance ? {
      value: balance.value,
      formatted: balance.formatted,
      symbol: balance.symbol,
    } : null,
    
    // Actions
    connectWallet,
    disconnectWallet,
    changeChain,
    
    // Modal state
    isModalOpen: walletState.isModalOpen,
    openWalletModal,
    closeWalletModal,
    
    // Available connectors
    connectors,
    
    // Error handling
    error: walletState.error || connectError?.message,
    
    // Utilities
    formatAddress,
  };

  return (
    <Web3Context.Provider value={value}>
      {children}
    </Web3Context.Provider>
  );
}

// Main Provider Component
export function Web3Provider({ children }) {
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <Web3ContextInner>
          {children}
        </Web3ContextInner>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

// Hook to use Web3 context
export function useWeb3() {
  const context = useContext(Web3Context);
  if (!context) {
    throw new Error('useWeb3 must be used within a Web3Provider');
  }
  return context;
}

export default Web3Provider;
