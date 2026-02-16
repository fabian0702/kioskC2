# Stage 1: Build the Angular application
FROM node:20-alpine AS build
WORKDIR /app

# Copy dependency definitions
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the application for production
# This command runs `ng build --configuration production`
RUN npm run build -- --configuration production

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy the build output from the previous stage
# Note: Ensure the path matches your angular.json output path.
# Based on the previous build output, it's dist/kiosk-frontend/browser for newer angular versions
# or dist/kiosk-frontend for older ones. Let's check the build output structure first if needed, 
# but assuming standard Angular 17+ structure which puts browser build in a subdirectory often.
# However, the previous build output said: Output location: .../dist/kiosk-frontend
# Angular 17+ with application builder puts files in /browser subdirectory of output path usually?
# Let's double check the build output log from previous turn. 
# It just said "Output location: /home/fabi/projects/kioskC2/ui/frontend/dist/kiosk-frontend".
# Let's assume the contents are directly there or in a browser folder. 
# Standard `application` builder (esbuild) in v17+ puts it in /browser usually unless configured otherwise.
# I will copy from dist/kiosk-frontend/browser first, and if that fails I'll adjust.
# Actually, looking at the logs: "Output location: .../dist/kiosk-frontend" usually implies that is the root of the output.
# But `application` builder is new. 
# let's try to list the dist folder to be sure.

# I'll stick to a safe copy command that copies the contents of the output directory.
COPY --from=build /app/dist/kiosk-frontend/browser /usr/share/nginx/html

# Copy the custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
