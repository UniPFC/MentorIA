/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './lib/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-right': 'slideInRight 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in-left': 'slideInLeft 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        'skeleton': 'skeleton 1.5s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'bounce-subtle': 'bounceSubtle 0.5s ease-out',
        'gradient': 'gradient 8s ease infinite',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
        'shimmer-slide': 'shimmerSlide 3s ease-in-out infinite',
        'slide-up-stagger-1': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.08s both',
        'slide-up-stagger-2': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.16s both',
        'slide-up-stagger-3': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.24s both',
        'slide-up-stagger-4': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.32s both',
        'slide-up-stagger-5': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        skeleton: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        bounceSubtle: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(99, 102, 241, 0.15), 0 0 30px rgba(99, 102, 241, 0.05)' },
          '50%': { boxShadow: '0 0 25px rgba(99, 102, 241, 0.3), 0 0 50px rgba(99, 102, 241, 0.1)' },
        },
        shimmerSlide: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      backgroundSize: {
        '300%': '300% 300%',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
