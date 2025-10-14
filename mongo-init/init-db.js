// MongoDB initialization script
// This script runs when the MongoDB container starts for the first time

// Switch to the product-management database
db = db.getSiblingDB('product-management');

// Create a user for the application
db.createUser({
  user: 'app_user',
  pwd: 'app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'product-management'
    }
  ]
});

// Create collections with sample data
db.createCollection('products');
db.createCollection('product-category');
db.createCollection('users');
db.createCollection('orders');
db.createCollection('customer_inquiries');

// Insert sample product categories
db['product-category'].insertMany([
  {
    name: 'Electronics',
    slug: 'electronics',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Clothing',
    slug: 'clothing', 
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Books',
    slug: 'books',
    status: 'active', 
    createdAt: new Date(),
    updatedAt: new Date()
  }
]);

// Insert sample products
db.products.insertMany([
  {
    name: 'iPhone 15 Pro',
    price: 999,
    discountPercentage: 5,
    category: 'Electronics',
    description: 'Latest iPhone with advanced camera system',
    thumbnail: 'https://example.com/iphone15.jpg',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'MacBook Pro M3',
    price: 1999,
    discountPercentage: 10,
    category: 'Electronics', 
    description: 'Powerful laptop for professionals',
    thumbnail: 'https://example.com/macbook.jpg',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Samsung Galaxy S24',
    price: 799,
    discountPercentage: 0,
    category: 'Electronics',
    description: 'Android flagship smartphone',
    thumbnail: 'https://example.com/galaxy.jpg', 
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Dell XPS 13',
    price: 1299,
    discountPercentage: 15,
    category: 'Electronics',
    description: 'Ultrabook with premium design',
    thumbnail: 'https://example.com/dell.jpg',
    status: 'active', 
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Nike Air Max',
    price: 120,
    discountPercentage: 20,
    category: 'Clothing',
    description: 'Comfortable running shoes',
    thumbnail: 'https://example.com/nike.jpg',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  }
]);

// Insert sample users
db.users.insertMany([
  {
    name: 'John Doe',
    email: 'john@example.com',
    password: '$2b$10$example_hash', // This would be a real bcrypt hash
    role: 'customer',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  },
  {
    name: 'Jane Smith', 
    email: 'jane@example.com',
    password: '$2b$10$example_hash',
    role: 'customer',
    status: 'active',
    createdAt: new Date(),
    updatedAt: new Date()
  }
]);

print('Database initialization completed successfully!');
print('Created collections: products, product-category, users, orders, customer_inquiries');
print('Inserted sample data for testing');
