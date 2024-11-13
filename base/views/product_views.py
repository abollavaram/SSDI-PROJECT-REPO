from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  # Import for pagination
from django.db.models import Q  
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from base.models import Product
from base.serializers import ProductSerializer
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def getProducts(request):
    query = request.query_params.get('keyword', '')
    sort_by = request.query_params.get('sort_by', 'name')  # Default sort by name
    order = request.query_params.get('order', 'asc')  # Default order ascending

    products = Product.objects.filter(name__icontains=query)

    # Sorting logic
    if sort_by in ['price', 'rating', 'name']:
        if order == 'desc':
            sort_by = f'-{sort_by}'
        products = products.order_by(sort_by)
    else:
        # Default sorting
        products = products.order_by('name')

    # Pagination
    page = request.query_params.get('page', 1)
    paginator = Paginator(products, 8)

    try:
        products = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        products = paginator.page(1)

    page = int(page)
    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response({'products': serializer.data, 'page': page, 'pages': paginator.num_pages})

@api_view(['GET'])
def getProduct(request, pk):
    try:
        product = Product.objects.get(_id=pk)
        serializer = ProductSerializer(product, many=False, context={'request': request})
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching product with ID {pk}: {e}")
        return Response({'detail': 'Error fetching product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def createProduct(request):
    try:
        user = request.user
        product = Product.objects.create(
            user=user,
            name='Sample Name',
            price=0,
            countInStock=0,
            description=''
        )
        serializer = ProductSerializer(product, many=False, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        return Response({'detail': 'Error creating product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteProduct(request, pk):
    try:
        product = Product.objects.get(_id=pk)
        product.delete()
        return Response({'detail': 'Product deleted successfully'}, status=status.HTTP_200_OK)
    except Product.DoesNotExist:
        return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting product with ID {pk}: {e}")
        return Response({'detail': 'Error deleting product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateProduct(request, pk):
    data = request.data
    product = Product.objects.get(_id=pk)

    product.name = data['name']
    product.price = data['price']
    product.countInStock = data['countInStock']
    product.description = data['description']

    product.save()

    serializer = ProductSerializer(product, many=False, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
def uploadImage(request):
    data = request.data

    product_id = data.get('product_id')
    product = Product.objects.get(_id=product_id)

    if 'image' in request.FILES:
        product.image = request.FILES['image']
        product.save()
        serializer = ProductSerializer(product, many=False, context={'request': request})
        return Response(serializer.data)
    else:
        return Response({'detail': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createProductReview(request, pk):
    user = request.user
    product = Product.objects.get(_id=pk)
    data = request.data

    # 1 - Review already exists
    alreadyExists = product.review_set.filter(user=user).exists()
    if alreadyExists:
        content = {'detail': 'Product already reviewed'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    # 2 - No Rating or 0
    elif data['rating'] == 0:
        content = {'detail': 'Please select a rating'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    # 3 - Create review
    else:
        review = Review.objects.create(
            user=user,
            product=product,
            name=user.first_name,
            rating=data['rating'],
            comment=data['comment'],
        )

        reviews = product.review_set.all()
        product.numReviews = len(reviews)

        total = 0
        for i in reviews:
            total += i.rating

        product.rating = total / len(reviews)
        product.save()

        return Response('Review Added')