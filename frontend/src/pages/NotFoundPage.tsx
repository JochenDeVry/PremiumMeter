import React from 'react';

const NotFoundPage: React.FC = () => {
  return (
    <div className="container">
      <h1>404 - Page Not Found</h1>
      <p>The page you're looking for doesn't exist.</p>
      <a href="/" className="button">
        Return Home
      </a>
    </div>
  );
};

export default NotFoundPage;
